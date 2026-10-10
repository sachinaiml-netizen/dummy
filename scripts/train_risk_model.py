#!/usr/bin/env python3
"""Train a transparent risk-score baseline on synthetic or outcome-labeled CSV data.

Synthetic mode proves the training/serving pipeline only. CSV mode expects
historical snapshots and a target explicitly labelled by project controls.
No third-party ML runtime dependency is required.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path
from typing import Any

FEATURE_SCHEMA = [
    {"key": "planned_progress_pct", "label": "Planned progress (%)"},
    {"key": "schedule_gap_pp", "label": "Schedule gap (percentage points)"},
    {"key": "positive_budget_variance_pct", "label": "Positive budget variance (%)"},
    {"key": "vendor_delay_days", "label": "Vendor delay (days)"},
    {"key": "open_issues", "label": "Unresolved issues"},
    {"key": "quality_defects", "label": "Quality defects"},
]
TARGET_COLUMN = "target_high_risk_30d"
GENERATOR_VERSION = "construction-risk-generator-v1"
RNG_MODULUS = 2147483647
RNG_MULTIPLIER = 16807


class StableRandom:
    """Small cross-language deterministic RNG so the checked-in artifact is reproducible."""

    def __init__(self, seed: int) -> None:
        self.state = seed % RNG_MODULUS
        if self.state <= 0:
            self.state += RNG_MODULUS - 1

    def random(self) -> float:
        self.state = (self.state * RNG_MULTIPLIER) % RNG_MODULUS
        return (self.state - 1) / (RNG_MODULUS - 1)

    def normal(self, mean: float, std: float) -> float:
        u1 = max(self.random(), 1e-12)
        u2 = self.random()
        return mean + std * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sigmoid(value: float) -> float:
    if value > 35:
        return 1.0
    if value < -35:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


def _features_from_values(
    planned_progress: float,
    actual_progress: float,
    budget_variance_pct: float,
    vendor_delay_days: float,
    open_issues: float,
    quality_defects: float,
) -> list[float]:
    return [
        planned_progress,
        max(0.0, planned_progress - actual_progress),
        max(0.0, budget_variance_pct),
        vendor_delay_days,
        open_issues,
        quality_defects,
    ]


def generate_synthetic_dataset(rows: int, seed: int) -> tuple[list[list[float]], list[int]]:
    """Generate invented telemetry and a probabilistic synthetic target—not real outcomes."""
    if isinstance(rows, bool) or not isinstance(rows, int) or rows < 300:
        raise ValueError("rows must be an integer of at least 300")
    rng = StableRandom(seed)
    x_rows: list[list[float]] = []
    targets: list[int] = []
    for _ in range(rows):
        planned = 5.0 + 95.0 * rng.random()
        raw_gap = rng.normal(2.0 + 8.0 * (planned / 100.0), 6.0 + 4.0 * (planned / 100.0))
        actual = _clamp(planned - raw_gap, 0.0, 105.0)
        gap = max(0.0, planned - actual)
        budget = _clamp(rng.normal(1.5 + 0.12 * gap, 7.0), -12.0, 35.0)
        vendor = min(45, math.floor(-8.0 * math.log(max(1e-12, 1.0 - rng.random())) + 0.5))
        issues = int(_clamp(math.floor(rng.normal(2.0 + 0.2 * vendor + 0.08 * gap, 3.5) + 0.5), 0, 40))
        defects = int(_clamp(math.floor(rng.normal(0.5 + 0.12 * issues + 0.04 * vendor, 2.0) + 0.5), 0, 25))
        features = [planned, gap, max(0.0, budget), float(vendor), float(issues), float(defects)]

        # Synthetic teacher function deliberately includes interactions the linear
        # baseline cannot perfectly represent. This is not an empirical risk definition.
        latent_logit = (
            -3.2
            + 0.006 * planned
            + 0.11 * gap
            + 0.05 * max(0.0, budget)
            + 0.07 * vendor
            + 0.11 * issues
            + 0.13 * defects
            + 0.0015 * gap * vendor
            + 0.018 * (max(0.0, issues - 8.0) ** 2) / 8.0
        )
        x_rows.append(features)
        targets.append(1 if rng.random() < _sigmoid(latent_logit) else 0)
    return x_rows, targets


def split_synthetic_indices(rows: int, seed: int) -> tuple[list[int], list[int], list[int]]:
    """Deterministic 70/15/15 split; rows were generated independently."""
    order = list(range(rows))
    rng = StableRandom(seed + 1)
    for index in range(len(order) - 1, 0, -1):
        swap_index = math.floor(rng.random() * (index + 1))
        order[index], order[swap_index] = order[swap_index], order[index]
    train_end = math.floor(rows * 0.70)
    validation_end = train_end + math.floor(rows * 0.15)
    return order[:train_end], order[train_end:validation_end], order[validation_end:]


def read_labeled_csv(path: str | Path) -> list[dict[str, Any]]:
    """Read real labelled snapshots; project IDs/dates are for splitting, never features."""
    required = {
        "project_id", "snapshot_date", "planned_progress", "actual_progress",
        "budget_variance_pct", "vendor_delay_days", "open_issues", "quality_defects",
        TARGET_COLUMN,
    }
    parsed: list[dict[str, Any]] = []
    seen_snapshots: set[tuple[str, str]] = set()
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV is missing a header row")
        headers = [name.strip().lower() if name else "" for name in reader.fieldnames]
        if len(set(headers)) != len(headers):
            raise ValueError("CSV contains duplicate column names")
        missing = sorted(required - set(headers))
        if missing:
            raise ValueError("CSV is missing required columns: " + ", ".join(missing))
        header_map = dict(zip(headers, reader.fieldnames))
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"Row {row_number} has more values than the header")
            raw = {key: row.get(header_map[key], "") for key in required}
            project_id = str(raw["project_id"] or "").strip()
            date_text = str(raw["snapshot_date"] or "").strip()
            if not project_id or len(project_id) > 80:
                raise ValueError(f"Row {row_number}: project_id is required and must be at most 80 characters")
            try:
                snapshot_date = dt.date.fromisoformat(date_text)
            except ValueError as exc:
                raise ValueError(f"Row {row_number}: snapshot_date must use YYYY-MM-DD") from exc
            key = (project_id, date_text)
            if key in seen_snapshots:
                raise ValueError(f"Row {row_number}: duplicate project_id/snapshot_date snapshot")
            seen_snapshots.add(key)

            def numeric(field: str, low: float, high: float, integer: bool = False) -> float:
                try:
                    value = float(str(raw[field]).strip())
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Row {row_number}: {field} must be numeric") from exc
                if not math.isfinite(value) or not low <= value <= high:
                    raise ValueError(f"Row {row_number}: {field} must be between {low:g} and {high:g}")
                if integer and not value.is_integer():
                    raise ValueError(f"Row {row_number}: {field} must be a whole number")
                return value

            planned = numeric("planned_progress", 0, 100)
            actual = numeric("actual_progress", 0, 100)
            budget = numeric("budget_variance_pct", -100, 500)
            vendor = numeric("vendor_delay_days", 0, 365, integer=True)
            issues = numeric("open_issues", 0, 10000, integer=True)
            defects = numeric("quality_defects", 0, 10000, integer=True)
            target_text = str(raw[TARGET_COLUMN] or "").strip()
            if target_text not in {"0", "1"}:
                raise ValueError(f"Row {row_number}: {TARGET_COLUMN} must be 0 or 1")
            parsed.append({
                "project_id": project_id,
                "snapshot_date": snapshot_date,
                "features": _features_from_values(planned, actual, budget, vendor, issues, defects),
                "target": int(target_text),
            })
    if len(parsed) < 100:
        raise ValueError("Labelled CSV must contain at least 100 valid snapshots")
    return parsed


def split_labeled_rows(
    rows: list[dict[str, Any]],
    embargo_days: int = 30,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int]:
    """Chronological 70/15/15 split with an embargo before validation/test periods."""
    if isinstance(embargo_days, bool) or not isinstance(embargo_days, int) or embargo_days < 0:
        raise ValueError("embargo_days must be a non-negative integer")
    dates = sorted({row["snapshot_date"] for row in rows})
    if len(dates) < 12:
        raise ValueError("Labeled CSV needs at least 12 distinct snapshot dates for a time-based holdout")
    first_cut = dates[max(1, math.floor(len(dates) * 0.70))]
    second_cut = dates[max(2, math.floor(len(dates) * 0.85))]
    validation_start = first_cut
    test_start = second_cut
    train_limit = first_cut - dt.timedelta(days=embargo_days)
    validation_limit = second_cut - dt.timedelta(days=embargo_days)

    train = [row for row in rows if row["snapshot_date"] < train_limit]
    validation = [
        row for row in rows
        if validation_start <= row["snapshot_date"] < validation_limit
    ]
    test = [row for row in rows if row["snapshot_date"] >= test_start]
    used = len(train) + len(validation) + len(test)
    dropped = len(rows) - used
    for name, subset in (("training", train), ("validation", validation), ("test", test)):
        if len(subset) < 30:
            raise ValueError(f"Time-based split leaves too few {name} rows ({len(subset)}); collect more dates/history")
        if len({row["target"] for row in subset}) < 2:
            raise ValueError(f"{name} partition must contain both target classes (0 and 1)")
    return train, validation, test, dropped


def fit_logistic_regression(
    x_train: list[list[float]],
    y_train: list[int],
    x_validation: list[list[float]],
    y_validation: list[int],
    max_epochs: int = 240,
    learning_rate: float = 0.12,
    l2: float = 0.0015,
    patience: int = 15,
) -> dict[str, Any]:
    if not x_train or len(x_train) != len(y_train):
        raise ValueError("training features and labels must be non-empty and aligned")
    if len(x_validation) != len(y_validation) or not x_validation:
        raise ValueError("validation features and labels must be non-empty and aligned")
    feature_count = len(x_train[0])
    if feature_count == 0 or any(len(row) != feature_count for row in x_train + x_validation):
        raise ValueError("all feature rows must have a consistent non-zero length")
    if set(y_train) != {0, 1} or set(y_validation) != {0, 1}:
        raise ValueError("training and validation partitions must both contain target classes 0 and 1")

    means = [sum(row[j] for row in x_train) / len(x_train) for j in range(feature_count)]
    scales = []
    for j in range(feature_count):
        variance = sum((row[j] - means[j]) ** 2 for row in x_train) / len(x_train)
        scales.append(math.sqrt(variance) or 1.0)

    weights = [0.0] * feature_count
    intercept = 0.0
    best: dict[str, Any] = {"loss": math.inf, "weights": None, "intercept": 0.0, "epoch": 0}
    wait = 0

    def validation_loss(current_weights: list[float], current_intercept: float) -> float:
        total = 0.0
        for row, target in zip(x_validation, y_validation):
            logit = current_intercept
            for j in range(feature_count):
                logit += current_weights[j] * ((row[j] - means[j]) / scales[j])
            probability = _clamp(_sigmoid(logit), 1e-12, 1.0 - 1e-12)
            total -= target * math.log(probability) + (1 - target) * math.log(1.0 - probability)
        return total / len(x_validation)

    for epoch in range(1, max_epochs + 1):
        weight_gradient = [0.0] * feature_count
        intercept_gradient = 0.0
        for row, target in zip(x_train, y_train):
            standardized = [(row[j] - means[j]) / scales[j] for j in range(feature_count)]
            logit = intercept + sum(weights[j] * standardized[j] for j in range(feature_count))
            error = _sigmoid(logit) - target
            intercept_gradient += error
            for j in range(feature_count):
                weight_gradient[j] += error * standardized[j]
        n = len(x_train)
        intercept -= learning_rate * intercept_gradient / n
        for j in range(feature_count):
            weights[j] -= learning_rate * (weight_gradient[j] / n + l2 * weights[j])

        val_loss = validation_loss(weights, intercept)
        if val_loss < best["loss"] - 1e-8:
            best = {
                "loss": val_loss,
                "weights": list(weights),
                "intercept": intercept,
                "epoch": epoch,
            }
            wait = 0
        else:
            wait += 1
        if wait >= patience:
            break
    best.update({"means": means, "scales": scales})
    return best


def evaluate_model(
    x_test: list[list[float]],
    y_test: list[int],
    model: dict[str, Any],
) -> dict[str, Any]:
    if len(x_test) != len(y_test) or not x_test:
        raise ValueError("test features and labels must be non-empty and aligned")
    scored: list[tuple[int, float]] = []
    for row, target in zip(x_test, y_test):
        logit = model["intercept"]
        for j, weight in enumerate(model["weights"]):
            logit += weight * ((row[j] - model["means"][j]) / model["scales"][j])
        scored.append((target, _sigmoid(logit)))

    tp = fp = tn = fn = correct = 0
    brier_sum = 0.0
    for target, probability in scored:
        prediction = 1 if probability >= 0.5 else 0
        correct += int(prediction == target)
        brier_sum += (probability - target) ** 2
        if prediction == 1 and target == 1:
            tp += 1
        elif prediction == 1:
            fp += 1
        elif target == 0:
            tn += 1
        else:
            fn += 1

    positives = sum(target for target, _ in scored)
    negatives = len(scored) - positives
    ranked = sorted(scored, key=lambda item: item[1])
    rank_sum = 0.0
    rank = 1
    index = 0
    while index < len(ranked):
        end = index + 1
        while end < len(ranked) and ranked[end][1] == ranked[index][1]:
            end += 1
        average_rank = (rank + (rank + end - index - 1)) / 2.0
        rank_sum += average_rank * sum(target for target, _ in ranked[index:end])
        rank += end - index
        index = end
    auc = (
        (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)
        if positives and negatives else 0.5
    )
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "test_rows": len(scored),
        "accuracy": round(correct / len(scored), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "roc_auc": round(auc, 4),
        "brier_score": round(brier_sum / len(scored), 4),
        "actual_positive_rate": round(positives / len(scored), 4),
        "majority_baseline_accuracy": round(max(positives, negatives) / len(scored), 4),
        "confusion_matrix": {
            "true_positive": tp, "false_positive": fp,
            "true_negative": tn, "false_negative": fn,
        },
    }


def _partition_summaries(
    x_rows: list[list[float]],
    targets: list[int],
    train_idx: list[int],
    validation_idx: list[int],
    test_idx: list[int],
) -> tuple[list[list[float]], list[int], list[list[float]], list[int], list[list[float]], list[int]]:
    return (
        [x_rows[i] for i in train_idx], [targets[i] for i in train_idx],
        [x_rows[i] for i in validation_idx], [targets[i] for i in validation_idx],
        [x_rows[i] for i in test_idx], [targets[i] for i in test_idx],
    )


def train(args: argparse.Namespace) -> dict[str, Any]:
    if args.input_csv:
        rows = read_labeled_csv(args.input_csv)
        train_rows, validation_rows, test_rows, dropped = split_labeled_rows(rows, args.embargo_days)
        x_train = [row["features"] for row in train_rows]
        y_train = [row["target"] for row in train_rows]
        x_validation = [row["features"] for row in validation_rows]
        y_validation = [row["target"] for row in validation_rows]
        x_test = [row["features"] for row in test_rows]
        y_test = [row["target"] for row in test_rows]
        data_kind = "labeled_historical_csv"
        split_strategy = f"chronological split with {args.embargo_days}-day embargo; project_id excluded from features"
        seed = None
        target_definition = (
            "Project-controls-labelled outcome within 30 days of snapshot. Define the event before training; "
            "the script does not infer labels from telemetry."
        )
        total_rows = len(rows)
    else:
        x_rows, targets = generate_synthetic_dataset(args.rows, args.seed)
        train_idx, validation_idx, test_idx = split_synthetic_indices(args.rows, args.seed)
        (
            x_train, y_train, x_validation, y_validation, x_test, y_test,
        ) = _partition_summaries(x_rows, targets, train_idx, validation_idx, test_idx)
        data_kind = "synthetic"
        split_strategy = "deterministic shuffled 70/15/15 split; independent generated records"
        seed = args.seed
        dropped = 0
        total_rows = args.rows
        target_definition = (
            "Synthetic indicator sampled from an invented risk generator; not observed construction outcome data."
        )

    for name, labels in (("training", y_train), ("validation", y_validation), ("test", y_test)):
        if len(labels) < 30 or set(labels) != {0, 1}:
            raise ValueError(f"{name} partition needs at least 30 rows and both target classes 0 and 1")

    fitted = fit_logistic_regression(
        x_train, y_train, x_validation, y_validation, max_epochs=args.max_epochs,
    )
    test_metrics = evaluate_model(x_test, y_test, fitted)
    artifact = {
        "model_version": args.model_version,
        "model_type": "standardized logistic regression",
        "training_data_kind": data_kind,
        "synthetic_generator_version": GENERATOR_VERSION if data_kind == "synthetic" else None,
        "target_column": TARGET_COLUMN,
        "target_definition": target_definition,
        "feature_schema": FEATURE_SCHEMA,
        "coefficients": fitted["weights"],
        "intercept": fitted["intercept"],
        "means": fitted["means"],
        "scales": fitted["scales"],
        "training_metadata": {
            "seed": seed,
            "total_rows": total_rows,
            "train_rows": len(y_train),
            "validation_rows": len(y_validation),
            "test_rows": len(y_test),
            "dropped_rows_for_embargo": dropped,
            "split_strategy": split_strategy,
            "selected_epoch": fitted["epoch"],
            "validation_log_loss": round(fitted["loss"], 5),
            "threshold_pct": {"low_below": 35, "medium_below": 65, "high_at_or_above": 65},
            "warning": (
                "Synthetic holdout metrics measure recovery of synthetic labels only; they do not estimate real-world "
                "construction performance."
                if data_kind == "synthetic"
                else "Candidate model only. Validate calibration, temporal generalization, subgroups and decision thresholds before use."
            ),
        },
        "test_metrics": test_metrics,
        "limitations": [
            "Scores are not guaranteed to be calibrated probabilities for the real target population.",
            "Synthetic training does not establish performance on Prestige or any real construction portfolio.",
            "Real-data training requires a precisely defined outcome observed after each snapshot.",
            "Deployment requires independent chronological validation, calibration, subgroup checks and human review.",
        ],
    }
    output_path = Path(args.output).resolve()
    serving_artifact = (Path(__file__).resolve().parents[1] / "app" / "risk_model.json").resolve()
    if args.input_csv and output_path == serving_artifact:
        raise ValueError(
            "Refusing to overwrite the active proof-model artifact with a real-data candidate. "
            "Write to a separate path, review metrics and approvals, then promote explicitly."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-csv", help="Optional outcome-labeled historical snapshots CSV.")
    parser.add_argument("--rows", type=int, default=60000, help="Synthetic rows generated when --input-csv is omitted.")
    parser.add_argument("--seed", type=int, default=20261010)
    parser.add_argument("--output", default="artifacts/risk_model_candidate.json")
    parser.add_argument("--model-version", default="synthetic-logistic-v1")
    parser.add_argument("--embargo-days", type=int, default=30)
    parser.add_argument("--max-epochs", type=int, default=240)
    args = parser.parse_args()
    try:
        result = train(args)
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))
    print(json.dumps({
        "output": str(Path(args.output)),
        "model_version": result["model_version"],
        "training_data_kind": result["training_data_kind"],
        "training_metadata": result["training_metadata"],
        "test_metrics": result["test_metrics"],
    }, indent=2))


if __name__ == "__main__":
    main()
