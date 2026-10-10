#!/usr/bin/env python3
"""Reproducibly train and evaluate an explicitly synthetic risk classifier.

No third-party ML packages are required. The labels are simulated, not real
construction outcomes. The exported CSV is for pipeline testing only.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "static" / "synthetic_risk_model.json"
SEED = 20261010
FEATURE_NAMES = [
    "schedule_gap_pp",
    "positive_budget_variance_pct",
    "vendor_delay_days",
    "open_issues",
    "quality_defects",
]


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def draw_count(
    rng: random.Random,
    low_probability: float,
    middle_probability: float,
    maximum: int,
    middle_high: int,
    high_low: int,
) -> int:
    draw = rng.random()
    if draw < low_probability:
        return rng.randint(0, min(4, maximum))
    if draw < low_probability + middle_probability:
        return rng.randint(5, min(middle_high, maximum))
    return rng.randint(min(high_low, maximum), maximum)


# A row is (model feature vector, simulated label, raw API-compatible inputs).
Row = tuple[list[float], int, dict[str, float | int]]


def make_dataset(count: int, seed: int, regime: str = "base") -> list[Row]:
    """Generate a repeatable mix of ordinary and tail-risk project snapshots."""
    rng = random.Random(seed)
    rows: list[Row] = []
    for _ in range(count):
        # Latent project pressure is intentionally not supplied to the model.
        pressure = rng.gauss(0.0, 1.0)
        planned = rng.uniform(5.0, 95.0)
        raw_gap = clamp(rng.gauss(3.0 + 5.2 * pressure, 7.0), -12.0, 42.0)
        if regime == "shifted":
            raw_gap = clamp(raw_gap + rng.gauss(3.0, 3.0), -12.0, 48.0)
        actual = clamp(planned - raw_gap, 0.0, 100.0)
        gap = max(0.0, planned - actual)

        budget = clamp(rng.gauss(1.5 + 0.18 * gap + 2.8 * pressure, 8.5), -25.0, 65.0)
        if regime == "shifted":
            budget = clamp(budget + rng.gauss(3.0, 5.0), -25.0, 75.0)

        vendor_draw = rng.random()
        if vendor_draw < 0.50:
            vendor = rng.randint(0, 2)
        elif vendor_draw < 0.82:
            vendor = rng.randint(3, 10)
        else:
            vendor = rng.randint(11, 40)
        if regime == "shifted" and rng.random() < 0.35:
            vendor = min(60, vendor + rng.randint(5, 18))

        issues = draw_count(
            rng,
            0.65 if regime == "base" else 0.48,
            0.25 if regime == "base" else 0.32,
            50 if regime == "base" else 70,
            20 if regime == "base" else 30,
            21 if regime == "base" else 31,
        )
        defects = draw_count(
            rng,
            0.78 if regime == "base" else 0.63,
            0.17 if regime == "base" else 0.25,
            25 if regime == "base" else 40,
            10 if regime == "base" else 18,
            11 if regime == "base" else 19,
        )

        features = [gap, max(0.0, budget), float(vendor), float(issues), float(defects)]
        interaction = 0.018 * max(gap - 10.0, 0.0) * min(vendor, 30.0) / 10.0
        # This is the synthetic teaching rule being approximated. Its values
        # are assumptions; they are not learned from construction observations.
        logit = (
            -3.2
            + 0.092 * features[0]
            + 0.026 * features[1]
            + 0.072 * features[2]
            + 0.038 * features[3]
            + 0.105 * features[4]
            + 0.42 * pressure
            + interaction
        )
        if regime == "shifted":
            # Deliberately alter prevalence and relationships for a drift check.
            logit += 0.35 + 0.018 * max(vendor - 10, 0) + 0.02 * max(issues - 15, 0)
        label = 1 if rng.random() < sigmoid(logit) else 0
        raw: dict[str, float | int] = {
            "planned_progress": round(planned, 4),
            "actual_progress": round(actual, 4),
            "budget_variance_pct": round(budget, 4),
            "vendor_delay_days": vendor,
            "open_issues": issues,
            "quality_defects": defects,
        }
        rows.append((features, label, raw))
    return rows


def standardizer(rows: list[Row]) -> tuple[list[float], list[float]]:
    means = [
        statistics.fmean(row[0][index] for row in rows)
        for index in range(len(FEATURE_NAMES))
    ]
    scales = []
    for index, mean in enumerate(means):
        variance = statistics.fmean((row[0][index] - mean) ** 2 for row in rows)
        scales.append(math.sqrt(variance) or 1.0)
    return means, scales


def transform(values: list[float], means: list[float], scales: list[float]) -> list[float]:
    return [(values[index] - means[index]) / scales[index] for index in range(len(values))]


def probability(values: list[float], coefficients: list[float], intercept: float) -> float:
    return sigmoid(intercept + sum(coef * value for coef, value in zip(coefficients, values)))


def binary_log_loss(predictions: list[float], labels: list[int]) -> float:
    epsilon = 1e-12
    return -sum(
        label * math.log(max(epsilon, min(1.0 - epsilon, prediction)))
        + (1 - label) * math.log(max(epsilon, min(1.0 - epsilon, 1.0 - prediction)))
        for prediction, label in zip(predictions, labels)
    ) / len(labels)


def evaluate(predictions: list[float], labels: list[int]) -> dict[str, Any]:
    ordered = sorted(zip(predictions, labels))
    positives = sum(labels)
    negatives = len(labels) - positives
    rank_sum = 0.0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end][0] == ordered[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        positive_in_group = sum(label for _, label in ordered[index:end])
        rank_sum += positive_in_group * average_rank
        index = end
    auc = (
        (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)
        if positives and negatives else 0.5
    )

    predicted_labels = [int(prediction >= 0.5) for prediction in predictions]
    true_positive = sum(prediction == 1 and label == 1 for prediction, label in zip(predicted_labels, labels))
    false_positive = sum(prediction == 1 and label == 0 for prediction, label in zip(predicted_labels, labels))
    false_negative = sum(prediction == 0 and label == 1 for prediction, label in zip(predicted_labels, labels))
    true_negative = sum(prediction == 0 and label == 0 for prediction, label in zip(predicted_labels, labels))
    return {
        "n": len(labels),
        "positive_rate": round(positives / len(labels), 6),
        "roc_auc": round(auc, 6),
        "brier_score": round(sum((prediction - label) ** 2 for prediction, label in zip(predictions, labels)) / len(labels), 6),
        "log_loss": round(binary_log_loss(predictions, labels), 6),
        "accuracy_at_0_5": round((true_positive + true_negative) / len(labels), 6),
        "confusion_at_0_5": {
            "tp": true_positive, "fp": false_positive,
            "tn": true_negative, "fn": false_negative,
        },
    }


def threshold_metrics(predictions: list[float], labels: list[int], threshold: float) -> dict[str, float | int]:
    predicted = [int(value >= threshold) for value in predictions]
    tp = sum(value == 1 and label == 1 for value, label in zip(predicted, labels))
    fp = sum(value == 1 and label == 0 for value, label in zip(predicted, labels))
    fn = sum(value == 0 and label == 1 for value, label in zip(predicted, labels))
    tn = sum(value == 0 and label == 0 for value, label in zip(predicted, labels))
    return {
        "flagged_pct": round(sum(predicted) / len(predicted), 6),
        "precision": round(tp / (tp + fp), 6) if tp + fp else 0.0,
        "recall": round(tp / (tp + fn), 6) if tp + fn else 0.0,
        "specificity": round(tn / (tn + fp), 6) if tn + fp else 0.0,
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def train_model(train: list[Row], validation: list[Row]) -> tuple[list[float], float, list[float], list[float], int, float]:
    means, scales = standardizer(train)
    train_x = [transform(row[0], means, scales) for row in train]
    train_y = [row[1] for row in train]
    validation_x = [transform(row[0], means, scales) for row in validation]
    validation_y = [row[1] for row in validation]

    coefficients = [0.0] * len(FEATURE_NAMES)
    prevalence = sum(train_y) / len(train_y)
    intercept = math.log(prevalence / (1.0 - prevalence))
    learning_rate = 0.35
    l2 = 0.002
    best_loss = float("inf")
    best_model: tuple[list[float], float] | None = None
    best_epoch = 0
    stagnant_epochs = 0

    # Full-batch logistic regression: deterministic and dependency-free.
    for epoch in range(1, 101):
        gradients = [0.0] * len(FEATURE_NAMES)
        intercept_gradient = 0.0
        for values, label in zip(train_x, train_y):
            error = probability(values, coefficients, intercept) - label
            intercept_gradient += error
            for index, value in enumerate(values):
                gradients[index] += error * value
        count = len(train_x)
        intercept -= learning_rate * intercept_gradient / count
        for index in range(len(coefficients)):
            coefficients[index] -= learning_rate * (
                gradients[index] / count + l2 * coefficients[index]
            )

        validation_predictions = [
            probability(values, coefficients, intercept) for values in validation_x
        ]
        validation_loss = binary_log_loss(validation_predictions, validation_y)
        if validation_loss < best_loss - 1e-7:
            best_loss = validation_loss
            best_model = (coefficients.copy(), intercept)
            best_epoch = epoch
            stagnant_epochs = 0
        else:
            stagnant_epochs += 1
        if stagnant_epochs >= 10:
            break

    assert best_model is not None
    return best_model[0], best_model[1], means, scales, best_epoch, best_loss


def build_artifact() -> tuple[dict[str, Any], dict[str, list[Row]]]:
    train = make_dataset(70_000, SEED, "base")
    validation = make_dataset(15_000, SEED + 1, "base")
    test = make_dataset(15_000, SEED + 2, "base")
    shifted = make_dataset(15_000, SEED + 3, "shifted")
    coefficients, intercept, means, scales, best_epoch, validation_loss = train_model(train, validation)

    def predictions(rows: list[Row]) -> tuple[list[float], list[int]]:
        return (
            [probability(transform(row[0], means, scales), coefficients, intercept) for row in rows],
            [row[1] for row in rows],
        )

    test_predictions, test_labels = predictions(test)
    shift_predictions, shift_labels = predictions(shifted)
    test_metrics = evaluate(test_predictions, test_labels)
    shift_metrics = evaluate(shift_predictions, shift_labels)
    test_review = threshold_metrics(test_predictions, test_labels, 0.25)
    shift_review = threshold_metrics(shift_predictions, shift_labels, 0.25)
    prevalence = sum(row[1] for row in train) / len(train)
    baseline_metrics = evaluate([prevalence] * len(test), test_labels)
    test_rows = len(test)
    artifact: dict[str, Any] = {
        "model_name": "Project Impact Lab Synthetic Risk Screening Model",
        "model_version": "0.1.0-synthetic",
        "model_status": "EXPERIMENTAL_SYNTHETIC_ONLY",
        "algorithm": "Standard-library logistic regression with standardized inputs and L2 regularization",
        "feature_names": FEATURE_NAMES,
        "feature_means": [round(value, 10) for value in means],
        "feature_scales": [round(value, 10) for value in scales],
        "coefficients": [round(value, 10) for value in coefficients],
        "intercept": round(intercept, 10),
        "decision_thresholds": {
            "watch": 0.25,
            "high": 0.50,
            "note": "Synthetic-validation screening cutoffs only; not calibrated business decision thresholds.",
        },
        "training": {
            "seed": SEED,
            "train_rows": len(train),
            "validation_rows": len(validation),
            "test_rows": len(test),
            "shift_stress_rows": len(shifted),
            "total_synthetic_rows_generated": len(train) + len(validation) + len(test) + len(shifted),
            "training_label_prevalence": round(prevalence, 6),
            "best_validation_epoch": best_epoch,
            "validation_log_loss": round(validation_loss, 6),
            "generator": "reproducible synthetic generator v1",
            "label_definition": (
                "Simulated Bernoulli label for elevated risk in the next reporting cycle, "
                "created by an authored rule with hidden project-pressure and interaction noise; "
                "not an observed construction outcome."
            ),
        },
        "evaluation": {
            "test": {
                "n": test_metrics["n"],
                "positive_rate": test_metrics["positive_rate"],
                "roc_auc": test_metrics["roc_auc"],
                "brier_score": test_metrics["brier_score"],
                "log_loss": test_metrics["log_loss"],
                "accuracy_at_0_5": test_metrics["accuracy_at_0_5"],
                "review_threshold_0_25": {
                    key: round(value, 6)
                    for key, value in test_review.items()
                    if key not in ("tp", "fp", "tn", "fn")
                },
                "review_threshold_confusion": {
                    key: test_review[key] for key in ("tp", "fp", "tn", "fn")
                },
                "constant_base_rate_baseline": {
                    "brier_score": baseline_metrics["brier_score"],
                    "log_loss": baseline_metrics["log_loss"],
                    "roc_auc": baseline_metrics["roc_auc"],
                },
            },
            "shift_stress": {
                "n": shift_metrics["n"],
                "positive_rate": shift_metrics["positive_rate"],
                "roc_auc": shift_metrics["roc_auc"],
                "brier_score": shift_metrics["brier_score"],
                "log_loss": shift_metrics["log_loss"],
                "review_threshold_0_25": {
                    key: round(value, 6)
                    for key, value in shift_review.items()
                    if key not in ("tp", "fp", "tn", "fn")
                },
                "review_threshold_confusion": {
                    key: shift_review[key] for key in ("tp", "fp", "tn", "fn")
                },
                "interpretation": (
                    "Intentionally shifted synthetic case only; changed feature frequencies "
                    "and label rule do not validate performance on real projects."
                ),
            },
        },
        "limitations": [
            "All examples and labels are synthetic and follow authored assumptions.",
            "Metrics apply only to generated holdout data from the same assumed generator.",
            "The shifted synthetic evaluation is not a real-world or Prestige validation set.",
            "The model is not trained on Prestige data and is not calibrated to real project outcomes or event rates.",
            "The score is not a contractual forecast, site-safety judgement, approval, or instruction to act.",
            "Before any real pilot, obtain permissioned historical project snapshots with outcome labels; evaluate on held-out projects and later time periods; compare to simple baselines; validate thresholds with project controls; then monitor drift and calibration.",
        ],
    }
    return artifact, {"train": train, "validation": validation, "test": test, "shift_stress": shifted}


def export_dataset(path: Path, splits: dict[str, list[Row]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "split", "project_id", "planned_progress", "actual_progress", "budget_variance_pct",
        "vendor_delay_days", "open_issues", "quality_defects", "synthetic_elevated_risk_label",
    ]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        row_number = 0
        for split_name, rows in splits.items():
            for _, label, raw in rows:
                row_number += 1
                writer.writerow({
                    "split": split_name,
                    "project_id": f"SYN-{split_name.upper()}-{row_number:06d}",
                    **raw,
                    "synthetic_elevated_risk_label": label,
                })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--check", action="store_true", help="Train and fail if the committed model artifact differs.")
    parser.add_argument("--export-dataset", type=Path, help="Optional path for a reproducible 115,000-row synthetic CSV.")
    args = parser.parse_args()

    artifact, splits = build_artifact()
    serialised = json.dumps(artifact, indent=2, ensure_ascii=False)
    if args.check:
        if not args.model_path.exists():
            raise SystemExit(f"Model artifact missing: {args.model_path}")
        existing = json.loads(args.model_path.read_text(encoding="utf-8"))
        if existing != artifact:
            raise SystemExit("Committed synthetic model artifact does not match the reproducible training pipeline.")
        print("Synthetic model reproduction check passed.")
    else:
        args.model_path.parent.mkdir(parents=True, exist_ok=True)
        args.model_path.write_text(serialised + "\n", encoding="utf-8")
        print(f"Trained model written to {args.model_path}")
    if args.export_dataset:
        export_dataset(args.export_dataset, splits)
        print(f"Exported {artifact['training']['total_synthetic_rows_generated']:,} synthetic rows to {args.export_dataset}")
    print(json.dumps({
        "version": artifact["model_version"],
        "train_rows": artifact["training"]["train_rows"],
        "validation_rows": artifact["training"]["validation_rows"],
        "test_metrics": artifact["evaluation"]["test"],
        "shift_stress_metrics": artifact["evaluation"]["shift_stress"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
