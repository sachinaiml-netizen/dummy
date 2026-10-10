from fastapi.testclient import TestClient

from app.main import app
from app.risk_model import MODEL, score_project
from app.schemas import ProjectTelemetry

client = TestClient(app)


def telemetry(**overrides):
    values = {
        "project_id": "DEMO-SNAPSHOT",
        "planned_progress": 80,
        "actual_progress": 58,
        "budget_variance_pct": 9,
        "vendor_delay_days": 10,
        "open_issues": 12,
        "quality_defects": 5,
    }
    values.update(overrides)
    return ProjectTelemetry(**values)


def test_artifact_documents_synthetic_training_and_holdout_scope():
    assert MODEL["training_data_kind"] == "synthetic"
    assert MODEL["training_metadata"]["total_rows"] == 60000
    assert MODEL["training_metadata"]["train_rows"] == 42000
    assert MODEL["training_metadata"]["validation_rows"] == 9000
    assert MODEL["training_metadata"]["test_rows"] == 9000
    assert MODEL["test_metrics"]["roc_auc"] > 0.70
    assert MODEL["test_metrics"]["accuracy"] > MODEL["test_metrics"]["majority_baseline_accuracy"]
    assert "do not estimate performance" in MODEL["training_metadata"]["warning"]


def test_trained_model_is_bounded_explainable_and_monotonic_for_schedule_gap():
    lower_gap = score_project(telemetry(actual_progress=78))
    higher_gap = score_project(telemetry(actual_progress=35))
    assert 0 <= lower_gap["score_pct"] <= 100
    assert 0 <= higher_gap["score_pct"] <= 100
    assert higher_gap["score_pct"] > lower_gap["score_pct"]
    assert len(higher_gap["feature_contributions"]) == 6
    assert len(higher_gap["top_drivers"]) == 3
    assert all("direction" in row and "logit_contribution" in row for row in higher_gap["feature_contributions"])
    assert "PROOF MODEL ONLY" in higher_gap["important_warning"]


def test_model_endpoint_returns_score_explanation_and_synthetic_metrics():
    response = client.post("/api/risk/proof-model", json={
        "project_id": "SYNTHETIC-TEST",
        "planned_progress": 80,
        "actual_progress": 58,
        "budget_variance_pct": 9,
        "vendor_delay_days": 10,
        "open_issues": 12,
        "quality_defects": 5,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["model_version"] == "synthetic-logistic-v1"
    assert result["training_data_kind"] == "synthetic"
    assert isinstance(result["score_pct"], float)
    assert result["risk_band"] in {"LOW", "MEDIUM", "HIGH"}
    assert result["test_metrics"]["test_rows"] == 9000
    assert "not a real-world event probability" in result["score_semantics"]
    assert "PROOF MODEL ONLY" in result["important_warning"]


def test_model_endpoint_preserves_input_validation():
    response = client.post("/api/risk/proof-model", json={
        "project_id": "BAD",
        "planned_progress": 101,
        "actual_progress": 50,
        "budget_variance_pct": 0,
        "vendor_delay_days": 0,
        "open_issues": 0,
        "quality_defects": 0,
    })
    assert response.status_code == 422


def test_training_generator_is_seed_reproducible_and_split_is_disjoint():
    from scripts.train_risk_model import generate_synthetic_dataset, split_synthetic_indices

    x1, y1 = generate_synthetic_dataset(500, 42)
    x2, y2 = generate_synthetic_dataset(500, 42)
    assert x1 == x2 and y1 == y2
    train, validation, test = split_synthetic_indices(500, 42)
    assert len(train) == 350
    assert len(validation) == 75
    assert len(test) == 75
    assert not (set(train) & set(validation))
    assert not (set(train) & set(test))
    assert not (set(validation) & set(test))



def _write_labeled_snapshot_csv(path, days=365, projects=6):
    import csv
    import datetime as dt

    start = dt.date(2024, 1, 1)
    fields = [
        "project_id", "snapshot_date", "planned_progress", "actual_progress",
        "budget_variance_pct", "vendor_delay_days", "open_issues",
        "quality_defects", "target_high_risk_30d",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for day_index in range(days):
            snapshot_date = (start + dt.timedelta(days=day_index)).isoformat()
            for project_index in range(projects):
                planned = 45 + project_index * 5
                gap = (day_index + project_index) % 18
                writer.writerow({
                    "project_id": f"PROJECT-{project_index:02d}",
                    "snapshot_date": snapshot_date,
                    "planned_progress": planned,
                    "actual_progress": max(0, planned - gap),
                    "budget_variance_pct": project_index - 2 + day_index % 7,
                    "vendor_delay_days": day_index % 9,
                    "open_issues": (day_index + project_index) % 15,
                    "quality_defects": (day_index + 2 * project_index) % 6,
                    "target_high_risk_30d": int((day_index + project_index) % 4 < 2),
                })


def test_labeled_csv_chronological_split_respects_embargo_and_keeps_classes(tmp_path):
    from app.risk_model import MODEL
    from scripts.train_risk_model import read_labeled_csv, split_labeled_rows

    path = tmp_path / "labeled.csv"
    _write_labeled_snapshot_csv(path)
    rows = read_labeled_csv(path)
    train, validation, test, dropped = split_labeled_rows(rows, embargo_days=30)

    assert len(rows) == 365 * 6
    assert len(train) >= 30 and len(validation) >= 30 and len(test) >= 30
    for partition in (train, validation, test):
        assert {row["target"] for row in partition} == {0, 1}
    assert max(row["snapshot_date"] for row in train) + __import__("datetime").timedelta(days=30) < min(row["snapshot_date"] for row in validation)
    assert max(row["snapshot_date"] for row in validation) + __import__("datetime").timedelta(days=30) < min(row["snapshot_date"] for row in test)
    assert dropped > 0
    # Project IDs are not model features; the active artifact is still synthetic.
    assert [feature["key"] for feature in MODEL["feature_schema"]] == [
        "planned_progress_pct", "schedule_gap_pp", "positive_budget_variance_pct",
        "vendor_delay_days", "open_issues", "quality_defects",
    ]


def test_labeled_csv_trains_candidate_without_replacing_committed_model(tmp_path):
    import argparse
    import json
    from scripts.train_risk_model import train

    source = tmp_path / "approved_labeled_snapshots.csv"
    _write_labeled_snapshot_csv(source)
    candidate_path = tmp_path / "candidate" / "risk-model-candidate.json"
    artifact = train(argparse.Namespace(
        input_csv=str(source),
        rows=60000,
        seed=20261010,
        output=str(candidate_path),
        model_version="test-labeled-candidate",
        embargo_days=30,
        max_epochs=35,
    ))

    assert candidate_path.is_file()
    on_disk = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert on_disk == artifact
    assert artifact["training_data_kind"] == "labeled_historical_csv"
    assert artifact["model_version"] == "test-labeled-candidate"
    assert artifact["training_metadata"]["seed"] is None
    assert artifact["training_metadata"]["dropped_rows_for_embargo"] > 0
    assert "chronological split with 30-day embargo" in artifact["training_metadata"]["split_strategy"]
    assert artifact["test_metrics"]["test_rows"] >= 30
    assert "Candidate model only" in artifact["training_metadata"]["warning"]
    # Candidate is written to the requested file only. Serving artifact remains the synthetic artifact.
    from app.risk_model import MODEL
    assert MODEL["training_data_kind"] == "synthetic"
    assert MODEL["model_version"] == "synthetic-logistic-v1"


def test_labeled_csv_rejects_invalid_target_dates_and_duplicate_snapshots(tmp_path):
    import csv
    from scripts.train_risk_model import read_labeled_csv

    path = tmp_path / "invalid.csv"
    _write_labeled_snapshot_csv(path, days=365, projects=1)
    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace("2024-01-01", "01/01/2024", 1), encoding="utf-8")
    try:
        read_labeled_csv(path)
    except ValueError as exc:
        assert "YYYY-MM-DD" in str(exc)
    else:
        raise AssertionError("Non-ISO snapshot dates should be rejected")

    _write_labeled_snapshot_csv(path, days=365, projects=1)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(rows[0])
    try:
        read_labeled_csv(path)
    except ValueError as exc:
        assert "duplicate project_id/snapshot_date" in str(exc)
    else:
        raise AssertionError("Duplicate historical snapshots should be rejected")


def test_labeled_csv_rejects_non_binary_outcomes(tmp_path):
    import csv
    from scripts.train_risk_model import read_labeled_csv

    path = tmp_path / "target.csv"
    _write_labeled_snapshot_csv(path, days=365, projects=1)
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = list(csv.DictReader(handle))
    reader[0]["target_high_risk_30d"] = "unknown"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=reader[0].keys())
        writer.writeheader()
        writer.writerows(reader)
    try:
        read_labeled_csv(path)
    except ValueError as exc:
        assert "must be 0 or 1" in str(exc)
    else:
        raise AssertionError("Non-binary observed outcome labels should be rejected")



def test_real_labeled_candidate_cannot_overwrite_active_serving_artifact(tmp_path):
    import argparse
    from pathlib import Path
    from scripts.train_risk_model import train

    source = tmp_path / "approved_labeled_snapshots.csv"
    _write_labeled_snapshot_csv(source, days=365, projects=6)
    serving_artifact = Path(__file__).resolve().parents[1] / "app" / "risk_model.json"
    original_bytes = serving_artifact.read_bytes()
    try:
        train(argparse.Namespace(
            input_csv=str(source),
            rows=60000,
            seed=20261010,
            output=str(serving_artifact),
            model_version="must-not-promote-automatically",
            embargo_days=30,
            max_epochs=35,
        ))
    except ValueError as exc:
        assert "Refusing to overwrite the active proof-model artifact" in str(exc)
    else:
        raise AssertionError("Real-data candidate must never overwrite active artifact automatically")
    assert serving_artifact.read_bytes() == original_bytes
