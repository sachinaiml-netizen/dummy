#!/usr/bin/env python3
"""Train a compact delay-risk classifier on generated or approved labelled snapshots.

Default training uses 50,000 synthetic rows. For real-data adaptation, provide a
CSV with one row per project snapshot, a binary outcome, and project_id/snapshot_date.
This script reads/writes local files only; it does not upload data.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, brier_score_loss, log_loss,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.risk_features import FEATURE_NAMES, PHASES, feature_values  # noqa: E402

ARTIFACT_DEFAULT = ROOT / "app" / "models" / "synthetic_delay_risk_v1.json"
TARGET = "material_delay_next_60d"
FEATURE_INPUT_FIELDS = [
    "planned_progress", "actual_progress", "budget_variance_pct", "vendor_delay_days",
    "open_issues", "quality_defects", "total_float_days", "float_consumed_pct",
    "procurement_delay_days", "long_lead_items_at_risk", "approval_overdue_days",
    "labour_shortage_pct", "weather_lost_days_30d", "design_changes_30d",
    "safety_actions_overdue", "phase",
]
RAW_FIELDS = ["project_id", "snapshot_date", *FEATURE_INPUT_FIELDS]
NUMERIC_RANGES = {
    "planned_progress": (0, 100), "actual_progress": (0, 100),
    "budget_variance_pct": (-100, 500), "vendor_delay_days": (0, 365),
    "open_issues": (0, 10000), "quality_defects": (0, 10000),
    "total_float_days": (-365, 365), "float_consumed_pct": (0, 1000),
    "procurement_delay_days": (0, 365), "long_lead_items_at_risk": (0, 500),
    "approval_overdue_days": (0, 365), "labour_shortage_pct": (0, 100),
    "weather_lost_days_30d": (0, 90), "design_changes_30d": (0, 365),
    "safety_actions_overdue": (0, 1000),
}


def generate_synthetic_rows(n_samples: int = 50_000, seed: int = 20261010) -> list[dict[str, Any]]:
    """Generate correlated phase-aware snapshots and noisy synthetic future labels.

    These rows are simulated examples, never observations of real projects. The
    binary target is generated from a probabilistic mechanism representing a
    material handover delay (>7 days) in the following 60 days.
    """
    if n_samples < 500:
        raise ValueError("Generate at least 500 rows for a meaningful synthetic run")
    rng = np.random.default_rng(seed)
    n = n_samples
    phase = rng.choice(np.array(PHASES), n, p=[.16, .30, .18, .20, .16])
    complexity = rng.beta(2.2, 3.2, n)
    friction = np.clip(rng.normal(.45 + .35 * complexity, .22, n), 0, 1.25)
    planned = rng.uniform(8, 98, n)
    gap_raw = np.clip(rng.normal(1.0 + 11 * friction + 2 * complexity, 4.8, n), -8, 35)
    actual = np.clip(planned - gap_raw, 0, 100)
    budget = np.clip(rng.normal(-1 + 10 * friction + 3 * complexity, 7.5, n), -18, 65)
    vendor = np.clip(np.round(rng.gamma(1.4, 2.4, n) + 18 * friction + 4 * complexity - 4), 0, 90).astype(int)
    procurement = np.clip(np.round(.58 * vendor + rng.gamma(1.2, 2.0, n) + 10 * friction - 3), 0, 90).astype(int)
    issues = np.clip(np.round(rng.poisson(2 + 11 * friction + 2 * complexity)), 0, 80).astype(int)
    defects = np.clip(np.round(rng.poisson(.5 + 5 * friction + 5 * (phase == "finishes") + 3 * (phase == "commissioning"))), 0, 60).astype(int)
    total_float = np.clip(np.round(rng.normal(27 - 38 * friction - 8 * complexity, 16)), -15, 90).astype(int)
    float_consumed = np.clip(rng.normal(25 + 78 * friction + 10 * complexity, 28, n), 0, 160)
    long_lead = np.clip(np.round(rng.poisson(1.5 + 5 * friction + 2 * complexity)), 0, 40).astype(int)
    approval = np.clip(np.round(rng.gamma(1.1, 2, n) + 12 * friction + 6 * complexity - 3), 0, 90).astype(int)
    labour = np.clip(rng.normal(10 + 38 * friction + 6 * complexity, 18, n), 0, 100)
    weather = np.clip(np.round(rng.poisson(1 + 4 * complexity)), 0, 30).astype(int)
    changes = np.clip(np.round(rng.poisson(.8 + 3.8 * complexity + 4 * (phase == "design"))), 0, 30).astype(int)
    safety = np.clip(np.round(rng.poisson(.3 + 3 * friction + 2 * complexity)), 0, 30).astype(int)

    is_design = (phase == "design").astype(float)
    is_structure = (phase == "structure").astype(float)
    is_site = np.isin(phase, ["structure", "envelope", "finishes"]).astype(float)
    is_early = np.isin(phase, ["design", "structure"]).astype(float)
    is_closeout = np.isin(phase, ["finishes", "commissioning"]).astype(float)
    positive_gap = np.maximum(planned - actual, 0)

    logit = (
        -4.85 + .065 * positive_gap + .022 * np.maximum(budget, 0)
        + .035 * vendor + .025 * issues + .028 * defects
        - .028 * np.maximum(total_float, 0) + .010 * float_consumed
        + .018 * procurement + .024 * long_lead
        + .015 * approval * is_early + .010 * labour * is_site
        + .035 * weather * is_site + .06 * changes * (is_design + is_structure)
        + .018 * safety + .35 * (procurement / 30) * (long_lead / 10)
        + .28 * (approval / 30) * is_early
        + .32 * (defects / 15) * is_closeout
        + .28 * (labour / 100) * is_site
        + .25 * (weather / 15) * is_site
        + .20 * (changes / 15) * (is_design + is_structure)
        + .30 * (float_consumed / 100) * (np.maximum(0, 15 - total_float) / 15)
        + .30 * (vendor / 30) * (positive_gap / 20)
        + .42 * complexity + .48 * friction + rng.normal(0, .50, n)
    )
    event_probability = 1 / (1 + np.exp(-np.clip(logit, -8, 8)))
    labels = rng.binomial(1, event_probability)
    base_date = np.datetime64("2024-01-01")
    day_offsets = rng.integers(0, 900, n)

    rows: list[dict[str, Any]] = []
    for i in range(n):
        rows.append({
            "project_id": f"SYN-PROJECT-{i + 1:06d}",
            "snapshot_date": str(base_date + np.timedelta64(int(day_offsets[i]), "D")),
            "planned_progress": round(float(planned[i]), 4),
            "actual_progress": round(float(actual[i]), 4),
            "budget_variance_pct": round(float(budget[i]), 4),
            "vendor_delay_days": int(vendor[i]),
            "open_issues": int(issues[i]),
            "quality_defects": int(defects[i]),
            "total_float_days": int(total_float[i]),
            "float_consumed_pct": round(float(float_consumed[i]), 4),
            "procurement_delay_days": int(procurement[i]),
            "long_lead_items_at_risk": int(long_lead[i]),
            "approval_overdue_days": int(approval[i]),
            "labour_shortage_pct": round(float(labour[i]), 4),
            "weather_lost_days_30d": int(weather[i]),
            "design_changes_30d": int(changes[i]),
            "safety_actions_overdue": int(safety[i]),
            "phase": str(phase[i]),
            TARGET: int(labels[i]),
        })
    return rows


def read_labeled_csv(path: Path, target_column: str) -> list[dict[str, Any]]:
    """Load approved labelled rows and validate required IDs, dates, units and target."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Input CSV is missing a header row")
        missing = sorted(set(RAW_FIELDS + [target_column]) - set(reader.fieldnames))
        if missing:
            raise ValueError("Input CSV is missing required columns: " + ", ".join(missing))
        rows: list[dict[str, Any]] = []
        for row_num, record in enumerate(reader, start=2):
            try:
                clean: dict[str, Any] = {
                    "project_id": (record.get("project_id") or "").strip(),
                    "snapshot_date": (record.get("snapshot_date") or "").strip(),
                }
                if not clean["project_id"]:
                    raise ValueError("project_id is blank")
                if len(clean["project_id"]) > 120:
                    raise ValueError("project_id exceeds 120 characters")
                if not clean["snapshot_date"]:
                    raise ValueError("snapshot_date is blank")
                date.fromisoformat(clean["snapshot_date"])
                for field in FEATURE_INPUT_FIELDS:
                    raw = (record.get(field) or "").strip()
                    if not raw:
                        raise ValueError(f"{field} is blank")
                    clean[field] = raw.lower() if field == "phase" else float(raw)
                if clean["phase"] not in PHASES:
                    raise ValueError(f"phase must be one of {', '.join(PHASES)}")
                for field, (lower, upper) in NUMERIC_RANGES.items():
                    value = clean[field]
                    if not math.isfinite(value) or value < lower or value > upper:
                        raise ValueError(f"{field} must be finite and between {lower} and {upper}")
                target_raw = (record.get(target_column) or "").strip()
                if target_raw not in {"0", "1"}:
                    raise ValueError(f"{target_column} must be 0 or 1")
                clean[target_column] = int(target_raw)
                rows.append(clean)
            except ValueError as exc:
                raise ValueError(f"Row {row_num}: {exc}") from exc

    if len(rows) < 200:
        raise ValueError("Labeled CSV needs at least 200 usable rows; larger representative samples are recommended")
    observations = [(row["project_id"], row["snapshot_date"]) for row in rows]
    if len(set(observations)) != len(observations):
        raise ValueError("Labeled CSV contains duplicate project_id + snapshot_date observations")
    labels = [row[target_column] for row in rows]
    if min(labels.count(0), labels.count(1)) < 20:
        raise ValueError("Labeled CSV needs at least 20 examples of each target class")
    if len({row["project_id"] for row in rows}) < 20:
        raise ValueError("Labeled CSV needs at least 20 distinct projects; 50+ are recommended")
    return rows


def metric_bundle(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predicted = probabilities >= .5
    prevalence = float(np.mean(y_true))
    baseline_brier = prevalence * (1 - prevalence)
    brier = float(brier_score_loss(y_true, probabilities))
    return {
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 4),
        "average_precision": round(float(average_precision_score(y_true, probabilities)), 4),
        "brier_score": round(brier, 4),
        "brier_skill_vs_prevalence_baseline": round(1 - brier / baseline_brier, 4) if baseline_brier else 0.0,
        "log_loss": round(float(log_loss(y_true, probabilities)), 4),
        "accuracy_at_0_5": round(float(accuracy_score(y_true, predicted)), 4),
        "precision_at_0_5": round(float(precision_score(y_true, predicted, zero_division=0)), 4),
        "recall_at_0_5": round(float(recall_score(y_true, predicted, zero_division=0)), 4),
        "positive_rate": round(prevalence, 4),
    }


def model_support_ranges(rows: list[dict[str, Any]], train_indices: np.ndarray, data_source: str) -> dict[str, Any]:
    """Define raw-input support from generator bounds or training-set percentiles."""
    if data_source == "synthetic_generator":
        return {
            "planned_progress": [8, 98], "actual_progress": [0, 100],
            "budget_variance_pct": [-18, 65], "vendor_delay_days": [0, 90],
            "open_issues": [0, 80], "quality_defects": [0, 60],
            "total_float_days": [-15, 90], "float_consumed_pct": [0, 160],
            "procurement_delay_days": [0, 90], "long_lead_items_at_risk": [0, 40],
            "approval_overdue_days": [0, 90], "labour_shortage_pct": [0, 100],
            "weather_lost_days_30d": [0, 30], "design_changes_30d": [0, 30],
            "safety_actions_overdue": [0, 30], "phase": list(PHASES),
        }
    training_rows = [rows[int(i)] for i in train_indices]
    support: dict[str, Any] = {}
    for field in FEATURE_INPUT_FIELDS:
        if field == "phase":
            support[field] = sorted({str(row[field]) for row in training_rows})
        else:
            values = np.asarray([float(row[field]) for row in training_rows], dtype=float)
            support[field] = [
                round(float(np.quantile(values, .01)), 6),
                round(float(np.quantile(values, .99)), 6),
            ]
    return support


def train(rows: list[dict[str, Any]], data_source: str, seed: int, output: Path,
          dataset_csv: Path | None = None) -> dict[str, Any]:
    labels = np.asarray([int(row[TARGET]) for row in rows], dtype=int)
    if min(int((labels == 0).sum()), int((labels == 1).sum())) < 20:
        raise ValueError("At least 20 examples per target class are required")
    matrix = np.asarray([feature_values(row) for row in rows], dtype=float)
    if not np.isfinite(matrix).all():
        raise ValueError("Feature matrix contains missing or non-finite values")
    groups = np.asarray([str(row["project_id"]) for row in rows])
    if len(set(groups)) < 20:
        raise ValueError("Need at least 20 distinct projects; 50+ are recommended")

    # Keep all snapshots from one project together so the same project cannot
    # appear in both training and holdout partitions.
    split_found = False
    for attempt in range(100):
        first = GroupShuffleSplit(n_splits=1, test_size=.30, random_state=seed + attempt)
        train_idx, temp_idx = next(first.split(matrix, labels, groups))
        if len(set(labels[train_idx])) < 2 or len(set(labels[temp_idx])) < 2:
            continue
        second = GroupShuffleSplit(n_splits=1, test_size=.50, random_state=seed + 1000 + attempt)
        val_rel, test_rel = next(second.split(matrix[temp_idx], labels[temp_idx], groups[temp_idx]))
        val_idx, test_idx = temp_idx[val_rel], temp_idx[test_rel]
        if len(set(labels[val_idx])) == 2 and len(set(labels[test_idx])) == 2:
            split_found = True
            break
    if not split_found:
        raise ValueError("Could not form project-disjoint splits with both classes; provide more diverse projects")

    x_train, y_train = matrix[train_idx], labels[train_idx]
    x_validation, y_validation = matrix[val_idx], labels[val_idx]
    x_test, y_test = matrix[test_idx], labels[test_idx]
    scaler = StandardScaler()
    model = LogisticRegression(C=.35, max_iter=1500, solver="lbfgs")
    model.fit(scaler.fit_transform(x_train), y_train)
    validation_prob = model.predict_proba(scaler.transform(x_validation))[:, 1]
    test_prob = model.predict_proba(scaler.transform(x_test))[:, 1]
    validation_metrics = metric_bundle(y_validation, validation_prob)
    test_metrics = metric_bundle(y_test, test_prob)
    if test_metrics["brier_skill_vs_prevalence_baseline"] <= 0:
        raise RuntimeError("Model failed to beat the holdout prevalence baseline on Brier score")

    artifact = {
        "model_name": "Float-Burn Watch Synthetic Delay Risk Model",
        "model_version": "0.1.0",
        "model_type": "standardized_logistic_regression",
        "task": TARGET,
        "target_definition": "Generated label for a material handover delay greater than 7 days during the next 60 days.",
        "feature_names": FEATURE_NAMES,
        "scaler_mean": [float(v) for v in scaler.mean_],
        "scaler_scale": [float(v) for v in scaler.scale_],
        "coefficients": [float(v) for v in model.coef_[0]],
        "intercept": float(model.intercept_[0]),
        "risk_band_thresholds": {"medium_at_or_above": .25, "high_at_or_above": .50},
        "data_source": data_source,
        "synthetic_seed": seed if data_source == "synthetic_generator" else None,
        "dataset_rows": len(rows),
        "split_rows": {"train": len(y_train), "validation": len(y_validation), "test": len(y_test)},
        "split_project_counts": {
            "train": len(set(groups[train_idx])),
            "validation": len(set(groups[val_idx])),
            "test": len(set(groups[test_idx])),
        },
        "class_counts": {"no_material_delay": int((labels == 0).sum()), "material_delay": int((labels == 1).sum())},
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "input_support_ranges": model_support_ranges(rows, train_idx, data_source),
        "trained_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "limitations": [
            "Synthetic-source metrics estimate performance only against this generated data mechanism.",
            "Risk percentages are not calibrated for Prestige or any real contractor/project portfolio.",
            "Splits are project-disjoint, but synthetic rows still share the same generator.",
            "No causal effect, actual cost, or approved recovery action is inferred.",
            "Real-data retraining requires authorized time-indexed snapshots and observed outcomes.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if dataset_csv:
        dataset_csv.parent.mkdir(parents=True, exist_ok=True)
        with dataset_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS + [TARGET])
            writer.writeheader()
            writer.writerows(rows)
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=50_000)
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--input-csv", type=Path, help="approved labelled CSV instead of generated data")
    parser.add_argument("--target-column", default=TARGET)
    parser.add_argument("--output", type=Path, default=ARTIFACT_DEFAULT)
    parser.add_argument("--dataset-csv", type=Path, help="optional local export of generated/training data")
    args = parser.parse_args()
    if args.input_csv:
        rows = read_labeled_csv(args.input_csv, args.target_column)
        if args.target_column != TARGET:
            for row in rows:
                row[TARGET] = int(row.pop(args.target_column))
        source = "approved_labelled_csv"
    else:
        rows = generate_synthetic_rows(args.samples, args.seed)
        source = "synthetic_generator"
    artifact = train(rows, source, args.seed, args.output, args.dataset_csv)
    print(json.dumps({
        "output": str(args.output), "data_source": artifact["data_source"],
        "dataset_rows": artifact["dataset_rows"], "split_rows": artifact["split_rows"],
        "split_project_counts": artifact["split_project_counts"],
        "class_counts": artifact["class_counts"], "validation_metrics": artifact["validation_metrics"],
        "test_metrics": artifact["test_metrics"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
