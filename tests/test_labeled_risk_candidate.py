import argparse
import csv
import datetime as dt
import json
from pathlib import Path

import pytest

from scripts.train_labeled_risk_candidate import (
    ACTIVE_SYNTHETIC_ARTIFACT,
    read_labeled_csv,
    split_labeled_rows,
    train_candidate,
)


OBSERVED_THROUGH = "2030-01-01"


def write_labeled_snapshots(path: Path, days: int = 420, projects: int = 10) -> None:
    fields = [
        "project_id", "snapshot_date", "planned_progress", "actual_progress",
        "budget_variance_pct", "vendor_delay_days", "open_issues", "quality_defects",
        "target_high_risk_30d",
    ]
    start = dt.date(2024, 1, 1)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for day_index in range(days):
            snapshot_date = start + dt.timedelta(days=day_index)
            for project_index in range(projects):
                event = int((day_index * 7 + project_index * 3) % 11 < 4)
                planned = 40 + (day_index + project_index) % 55
                gap = (8 if event else 1) + day_index % 4
                writer.writerow({
                    "project_id": f"PROJECT-{project_index:02d}",
                    "snapshot_date": snapshot_date.isoformat(),
                    "planned_progress": planned,
                    "actual_progress": max(0, planned - gap),
                    "budget_variance_pct": (8 if event else 0) + day_index % 3,
                    "vendor_delay_days": (6 if event else 0) + day_index % 4,
                    "open_issues": (9 if event else 0) + project_index % 3 + day_index % 2,
                    "quality_defects": (3 if event else 0) + day_index % 3,
                    "target_high_risk_30d": event,
                })


def args_for(source: Path, output: Path):
    return argparse.Namespace(
        input_csv=str(source),
        target_definition="Project-controls-reviewed material handover delay within 30 days of the snapshot.",
        outcomes_observed_through=OBSERVED_THROUGH,
        output=str(output),
        model_version="test-candidate-v1",
        embargo_days=30,
        held_out_project_fraction=0.2,
        overwrite_candidate=False,
    )


def test_labeled_csv_split_has_embargo_and_unseen_project_test(tmp_path):
    source = tmp_path / "approved_labeled_snapshots.csv"
    write_labeled_snapshots(source)
    rows = read_labeled_csv(source, OBSERVED_THROUGH)
    split = split_labeled_rows(rows, embargo_days=30, held_out_project_fraction=0.2)

    train_projects = {row["project_id"] for row in split["train"]}
    validation_projects = {row["project_id"] for row in split["validation"]}
    heldout_test_projects = {row["project_id"] for row in split["heldout_project_test"]}

    assert len(rows) == 420 * 10
    assert train_projects == validation_projects
    assert train_projects.isdisjoint(heldout_test_projects)
    assert len(split["temporal_test"]) >= 30
    assert len(split["heldout_project_test"]) >= 30
    assert max(row["snapshot_date"] for row in split["train"]) + dt.timedelta(days=30) < min(
        row["snapshot_date"] for row in split["validation"]
    )
    assert max(row["snapshot_date"] for row in split["validation"]) + dt.timedelta(days=30) < min(
        row["snapshot_date"] for row in split["temporal_test"] + split["heldout_project_test"]
    )


def test_labeled_candidate_trains_and_reports_two_independent_future_tests(tmp_path):
    source = tmp_path / "approved_labeled_snapshots.csv"
    output = tmp_path / "candidate" / "risk_model_candidate.json"
    write_labeled_snapshots(source)
    active_before = ACTIVE_SYNTHETIC_ARTIFACT.read_bytes()

    artifact = train_candidate(args_for(source, output))

    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8")) == artifact
    assert artifact["model_status"] == "CANDIDATE_REAL_LABELLED_NOT_ACTIVE"
    assert artifact["training_data_kind"] == "labeled_historical_csv"
    assert artifact["training"]["train_rows"] > 100
    assert artifact["training"]["validation_rows"] > 30
    assert artifact["training"]["future_temporal_test_rows"] > 30
    assert artifact["training"]["future_heldout_project_test_rows"] > 30
    assert artifact["evaluation"]["future_temporal_test"]["roc_auc"] >= 0
    assert artifact["evaluation"]["future_heldout_project_test"]["brier_score"] >= 0
    assert artifact["training"]["raw_rows_in_candidate"] is False
    assert "project_id" not in json.dumps(artifact)
    assert "not auto-promoted" not in json.dumps(artifact).lower() or artifact["model_status"].startswith("CANDIDATE")
    assert ACTIVE_SYNTHETIC_ARTIFACT.read_bytes() == active_before


def test_real_candidate_refuses_to_overwrite_active_synthetic_artifact(tmp_path):
    source = tmp_path / "approved_labeled_snapshots.csv"
    write_labeled_snapshots(source)
    active_before = ACTIVE_SYNTHETIC_ARTIFACT.read_bytes()
    args = args_for(source, ACTIVE_SYNTHETIC_ARTIFACT)

    with pytest.raises(ValueError, match="Refusing to overwrite the active synthetic proof model"):
        train_candidate(args)

    assert ACTIVE_SYNTHETIC_ARTIFACT.read_bytes() == active_before


def test_real_candidate_requires_mature_30_day_outcome_window(tmp_path):
    source = tmp_path / "approved_labeled_snapshots.csv"
    write_labeled_snapshots(source, days=420, projects=10)
    last_snapshot = (dt.date(2024, 1, 1) + dt.timedelta(days=419)).isoformat()

    with pytest.raises(ValueError, match="30-day outcome window is not fully observed"):
        read_labeled_csv(source, last_snapshot)


def test_real_candidate_rejects_unlabelled_or_ambiguous_target(tmp_path):
    source = tmp_path / "approved_labeled_snapshots.csv"
    write_labeled_snapshots(source)
    content = source.read_text(encoding="utf-8")
    source.write_text(content.replace(",1\n", ",unknown\n", 1), encoding="utf-8")

    with pytest.raises(ValueError, match="target_high_risk_30d must be 0 or 1"):
        read_labeled_csv(source, OBSERVED_THROUGH)


def test_real_candidate_does_not_accept_single_project_dataset(tmp_path):
    source = tmp_path / "one_project.csv"
    write_labeled_snapshots(source, days=420, projects=1)

    with pytest.raises(ValueError, match="at least 5 distinct projects"):
        read_labeled_csv(source, OBSERVED_THROUGH)
