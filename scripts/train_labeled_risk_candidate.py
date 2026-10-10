#!/usr/bin/env python3
"""Train and evaluate a real-label risk-model candidate without promoting it.

The CSV must contain observed, project-controls-approved outcomes. No labels are
inferred from telemetry. The active synthetic proof model is never overwritten.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.train_synthetic_risk_model import (  # noqa: E402
    FEATURE_NAMES,
    Row,
    evaluate,
    probability,
    threshold_metrics,
    train_model,
    transform,
)

TARGET_COLUMN = "target_high_risk_30d"
DEFAULT_OUTPUT = ROOT / "artifacts" / "risk_model_candidate.json"
ACTIVE_SYNTHETIC_ARTIFACT = ROOT / "static" / "synthetic_risk_model.json"
MIN_ROWS_PER_PARTITION = 30


def _iso_date(value: str, row_number: int) -> dt.date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"Row {row_number}: snapshot_date must use YYYY-MM-DD")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: snapshot_date is not a valid date") from exc


def read_labeled_csv(path: str | Path, outcomes_observed_through: str) -> list[dict[str, Any]]:
    """Validate labeled snapshots; dates and project IDs are used only for splitting."""
    observed_through = _iso_date(outcomes_observed_through, 1)
    required = {
        "project_id", "snapshot_date", "planned_progress", "actual_progress",
        "budget_variance_pct", "vendor_delay_days", "open_issues", "quality_defects",
        TARGET_COLUMN,
    }
    parsed: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV is missing its header row")
        normalized = [field.strip().lower() if field else "" for field in reader.fieldnames]
        if any(not field for field in normalized):
            raise ValueError("CSV headers must not be blank")
        if len(set(normalized)) != len(normalized):
            raise ValueError("CSV contains duplicate column names after normalization")
        missing = sorted(required - set(normalized))
        if missing:
            raise ValueError("CSV is missing required columns: " + ", ".join(missing))
        header_map = dict(zip(normalized, reader.fieldnames))

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Row {row_number} has more values than the header")
            if all(value is None or not str(value).strip() for value in row.values()):
                continue

            def text_field(name: str) -> str:
                value = row.get(header_map[name])
                return "" if value is None else str(value).strip()

            project_id = text_field("project_id")
            if not project_id or len(project_id) > 80:
                raise ValueError(f"Row {row_number}: project_id is required and must be at most 80 characters")
            date_text = text_field("snapshot_date")
            snapshot_date = _iso_date(date_text, row_number)
            if snapshot_date + dt.timedelta(days=30) > observed_through:
                raise ValueError(
                    f"Row {row_number}: the 30-day outcome window is not fully observed by "
                    f"{observed_through.isoformat()}"
                )
            key = (project_id, date_text)
            if key in seen:
                raise ValueError(f"Row {row_number}: duplicate project_id/snapshot_date snapshot")
            seen.add(key)

            def numeric(name: str, low: float, high: float, integer: bool = False) -> float:
                raw = text_field(name)
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(f"Row {row_number}: {name} must be numeric") from exc
                if not math.isfinite(value) or not low <= value <= high:
                    raise ValueError(f"Row {row_number}: {name} must be between {low:g} and {high:g}")
                if integer and not value.is_integer():
                    raise ValueError(f"Row {row_number}: {name} must be a whole number")
                return value

            planned = numeric("planned_progress", 0, 100)
            actual = numeric("actual_progress", 0, 100)
            budget = numeric("budget_variance_pct", -100, 500)
            vendor = numeric("vendor_delay_days", 0, 365, integer=True)
            issues = numeric("open_issues", 0, 10000, integer=True)
            defects = numeric("quality_defects", 0, 10000, integer=True)
            label_text = text_field(TARGET_COLUMN)
            if label_text not in {"0", "1"}:
                raise ValueError(f"Row {row_number}: {TARGET_COLUMN} must be 0 or 1")

            feature_values = [
                max(0.0, planned - actual),
                max(0.0, budget),
                float(vendor),
                float(issues),
                float(defects),
            ]
            parsed.append({
                "project_id": project_id,
                "snapshot_date": snapshot_date,
                "features": feature_values,
                "target": int(label_text),
            })

    if len(parsed) < 100:
        raise ValueError("Labelled CSV must contain at least 100 valid snapshots")
    if len({row["snapshot_date"] for row in parsed}) < 12:
        raise ValueError("Labelled CSV must contain at least 12 distinct snapshot dates")
    if len({row["project_id"] for row in parsed}) < 5:
        raise ValueError("Project-held-out evaluation needs at least 5 distinct projects")
    parsed.sort(key=lambda row: (row["snapshot_date"], row["project_id"]))
    return parsed


def split_labeled_rows(
    rows: list[dict[str, Any]],
    embargo_days: int = 30,
    held_out_project_fraction: float = 0.2,
) -> dict[str, Any]:
    """Use a chronological validation window plus future tests for known and unseen projects."""
    if isinstance(embargo_days, bool) or not isinstance(embargo_days, int) or embargo_days < 0:
        raise ValueError("embargo_days must be a non-negative integer")
    if not math.isfinite(held_out_project_fraction) or not 0.1 <= held_out_project_fraction <= 0.4:
        raise ValueError("held_out_project_fraction must be between 0.10 and 0.40")

    projects = sorted({row["project_id"] for row in rows})
    if len(projects) < 5:
        raise ValueError("At least 5 projects are required for project-held-out evaluation")
    held_out_count = max(1, math.ceil(len(projects) * held_out_project_fraction))
    if held_out_count >= len(projects) - 2:
        raise ValueError("Project holdout would leave too few development projects")
    hashed = sorted(
        projects,
        key=lambda project_id: hashlib.sha256(
            ("project-impact-lab-risk-holdout-v1:" + project_id).encode("utf-8")
        ).hexdigest(),
    )
    held_out_projects = set(hashed[:held_out_count])
    development_projects = set(projects) - held_out_projects

    dates = sorted({row["snapshot_date"] for row in rows})
    if len(dates) < 12:
        raise ValueError("At least 12 distinct dates are required for time-separated evaluation")
    first_cut = dates[min(len(dates) - 2, max(1, math.floor(len(dates) * 0.70)))]
    second_cut = dates[min(len(dates) - 1, max(2, math.floor(len(dates) * 0.85)))]
    if first_cut >= second_cut:
        raise ValueError("Not enough distinct dates to form chronological partitions")

    train_before = first_cut - dt.timedelta(days=embargo_days)
    validation_before = second_cut - dt.timedelta(days=embargo_days)
    train = [
        row for row in rows
        if row["project_id"] in development_projects and row["snapshot_date"] < train_before
    ]
    validation = [
        row for row in rows
        if row["project_id"] in development_projects
        and first_cut <= row["snapshot_date"] < validation_before
    ]
    temporal_test = [
        row for row in rows
        if row["project_id"] in development_projects and row["snapshot_date"] >= second_cut
    ]
    project_test = [
        row for row in rows
        if row["project_id"] in held_out_projects and row["snapshot_date"] >= second_cut
    ]

    for name, subset in (
        ("training", train),
        ("validation", validation),
        ("future temporal test", temporal_test),
        ("future held-out-project test", project_test),
    ):
        if len(subset) < MIN_ROWS_PER_PARTITION:
            raise ValueError(
                f"{name} partition has only {len(subset)} rows; at least "
                f"{MIN_ROWS_PER_PARTITION} are required. Supply more projects/history or revise "
                "the holdout configuration before fitting."
            )
        if {row["target"] for row in subset} != {0, 1}:
            raise ValueError(f"{name} partition must contain both target classes (0 and 1)")

    if set(row["project_id"] for row in project_test) & set(row["project_id"] for row in train):
        raise ValueError("Project leakage detected between training and held-out-project test")
    if max(row["snapshot_date"] for row in train) + dt.timedelta(days=embargo_days) >= min(
        row["snapshot_date"] for row in validation
    ):
        raise ValueError("Temporal embargo failed between training and validation")
    if max(row["snapshot_date"] for row in validation) + dt.timedelta(days=embargo_days) >= min(
        row["snapshot_date"] for row in temporal_test + project_test
    ):
        raise ValueError("Temporal embargo failed between validation and future tests")

    used = len(train) + len(validation) + len(temporal_test) + len(project_test)
    return {
        "train": train,
        "validation": validation,
        "temporal_test": temporal_test,
        "heldout_project_test": project_test,
        "held_out_project_count": len(held_out_projects),
        "development_project_count": len(development_projects),
        "held_out_project_ids": held_out_projects,
        "development_project_ids": development_projects,
        "first_validation_date": first_cut,
        "future_test_start_date": second_cut,
        "dropped_rows": len(rows) - used,
    }


def _as_training_rows(rows: list[dict[str, Any]]) -> list[Row]:
    # Project IDs and dates intentionally do not enter the model's feature vector.
    return [(row["features"], row["target"], {}) for row in rows]


def _evaluate_partition(rows: list[dict[str, Any]], fitted: dict[str, Any]) -> dict[str, Any]:
    probabilities = [
        probability(
            transform(row["features"], fitted["means"], fitted["scales"]),
            fitted["weights"],
            fitted["intercept"],
        )
        for row in rows
    ]
    labels = [row["target"] for row in rows]
    metrics = evaluate(probabilities, labels)
    metrics["research_threshold_0_25"] = threshold_metrics(probabilities, labels, 0.25)
    prevalence = sum(labels) / len(labels)
    baseline = evaluate([prevalence] * len(labels), labels)
    metrics["constant_partition_prevalence_baseline"] = {
        "brier_score": baseline["brier_score"],
        "log_loss": baseline["log_loss"],
        "roc_auc": baseline["roc_auc"],
    }
    return metrics


def train_candidate(args: argparse.Namespace) -> dict[str, Any]:
    output_path = Path(args.output).resolve()
    active_path = ACTIVE_SYNTHETIC_ARTIFACT.resolve()
    if output_path == active_path:
        raise ValueError(
            "Refusing to overwrite the active synthetic proof model. Write a candidate to a separate path."
        )
    if output_path.exists() and not args.overwrite_candidate:
        raise ValueError(
            f"Candidate output already exists: {output_path}. Choose another path or pass --overwrite-candidate."
        )

    rows = read_labeled_csv(args.input_csv, args.outcomes_observed_through)
    splits = split_labeled_rows(
        rows,
        embargo_days=args.embargo_days,
        held_out_project_fraction=args.held_out_project_fraction,
    )
    fitted_tuple = train_model(
        _as_training_rows(splits["train"]),
        _as_training_rows(splits["validation"]),
    )
    coefficients, intercept, means, scales, selected_epoch, validation_loss = fitted_tuple
    fitted = {
        "weights": coefficients,
        "intercept": intercept,
        "means": means,
        "scales": scales,
    }
    temporal_metrics = _evaluate_partition(splits["temporal_test"], fitted)
    project_metrics = _evaluate_partition(splits["heldout_project_test"], fitted)
    all_partitions = [splits["train"], splits["validation"], splits["temporal_test"], splits["heldout_project_test"]]
    used = sum(len(partition) for partition in all_partitions)
    date_min = min(row["snapshot_date"] for row in rows)
    date_max = max(row["snapshot_date"] for row in rows)

    candidate = {
        "model_name": "Project Impact Lab Historical Risk Candidate",
        "model_version": args.model_version,
        "model_status": "CANDIDATE_REAL_LABELLED_NOT_ACTIVE",
        "algorithm": "Standard-library logistic regression with standardized inputs, L2 regularization and validation-loss early stopping",
        "training_data_kind": "labeled_historical_csv",
        "target_column": TARGET_COLUMN,
        "target_definition": args.target_definition,
        "feature_names": FEATURE_NAMES,
        "feature_means": [round(value, 10) for value in means],
        "feature_scales": [round(value, 10) for value in scales],
        "coefficients": [round(value, 10) for value in coefficients],
        "intercept": round(intercept, 10),
        "decision_thresholds": {
            "research_only": [0.25, 0.50],
            "note": "Illustrative review thresholds only. No real-world operating threshold is approved by this training script.",
        },
        "training": {
            "total_rows_read": len(rows),
            "used_rows": used,
            "dropped_rows_for_embargo_and_group_holdout": splits["dropped_rows"],
            "train_rows": len(splits["train"]),
            "validation_rows": len(splits["validation"]),
            "future_temporal_test_rows": len(splits["temporal_test"]),
            "future_heldout_project_test_rows": len(splits["heldout_project_test"]),
            "distinct_projects": len({row["project_id"] for row in rows}),
            "development_project_count": splits["development_project_count"],
            "held_out_project_count": splits["held_out_project_count"],
            "earliest_snapshot_date": date_min.isoformat(),
            "latest_snapshot_date": date_max.isoformat(),
            "first_validation_date": splits["first_validation_date"].isoformat(),
            "future_test_start_date": splits["future_test_start_date"].isoformat(),
            "outcomes_observed_through": args.outcomes_observed_through,
            "embargo_days": args.embargo_days,
            "project_holdout_fraction": args.held_out_project_fraction,
            "split_strategy": (
                "Chronological train/validation split with an embargo; two future-period tests: "
                "projects seen in development and fully held-out projects. Project IDs/dates are split keys only, not features."
            ),
            "selected_epoch": selected_epoch,
            "validation_log_loss": round(validation_loss, 6),
            "raw_rows_in_candidate": False,
        },
        "evaluation": {
            "future_temporal_test": temporal_metrics,
            "future_heldout_project_test": project_metrics,
        },
        "limitations": [
            "This candidate is not the active serving model and is not auto-promoted.",
            "Metrics depend on target correctness, target prevalence, snapshot freshness and whether features were available at prediction time.",
            "Temporal testing on development projects and a future test on held-out projects are stronger checks, but do not prove external validity for every project, asset class or geography.",
            "A model trained on a small or biased portfolio may not generalize to a broader construction portfolio.",
            "Thresholds require cost-sensitive review, calibration, subgroup/error analysis, comparison with simple baselines and project-controls approval.",
            "Do not use for site safety, contractual action, price, staffing or handover decisions without a governed validation and human-review process.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return candidate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", required=True, help="Approved, outcome-labelled historical snapshots CSV.")
    parser.add_argument("--target-definition", required=True, help="Human-readable definition of what label 1 means.")
    parser.add_argument("--outcomes-observed-through", required=True, help="Latest date through which all 30-day outcomes are observed (YYYY-MM-DD).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model-version", default="historical-risk-candidate-v1")
    parser.add_argument("--embargo-days", type=int, default=30)
    parser.add_argument("--held-out-project-fraction", type=float, default=0.2)
    parser.add_argument("--overwrite-candidate", action="store_true", help="Explicitly replace an existing candidate file (never the active proof model).")
    args = parser.parse_args()
    try:
        candidate = train_candidate(args)
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "candidate_output": str(Path(args.output).resolve()),
        "model_version": candidate["model_version"],
        "model_status": candidate["model_status"],
        "target_definition": candidate["target_definition"],
        "training": candidate["training"],
        "evaluation": candidate["evaluation"],
        "warning": "Candidate is not active and is not approved for decisions.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
