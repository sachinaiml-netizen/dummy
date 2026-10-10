from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from .schemas import ProjectTelemetry

MODEL_PATH = Path(__file__).resolve().parent.parent / "static" / "synthetic_risk_model.json"
EXPECTED_FEATURES = [
    "schedule_gap_pp",
    "positive_budget_variance_pct",
    "vendor_delay_days",
    "open_issues",
    "quality_defects",
]

DISPLAY_NAMES = {
    "schedule_gap_pp": "Schedule gap",
    "positive_budget_variance_pct": "Positive budget variance",
    "vendor_delay_days": "Vendor delay",
    "open_issues": "Open issues",
    "quality_defects": "Quality defects",
}


@lru_cache(maxsize=1)
def load_model() -> dict[str, Any]:
    """Load the small, versioned model artifact; no training happens at request time."""
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"Synthetic risk model artifact is missing: {MODEL_PATH}")
    artifact = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    if artifact.get("feature_names") != EXPECTED_FEATURES:
        raise RuntimeError("Synthetic risk model feature order does not match the serving code.")
    arrays = ("feature_means", "feature_scales", "coefficients")
    if any(len(artifact.get(name, [])) != len(EXPECTED_FEATURES) for name in arrays):
        raise RuntimeError("Synthetic risk model has an invalid feature array length.")
    if any(not math.isfinite(float(value)) for name in arrays for value in artifact[name]):
        raise RuntimeError("Synthetic risk model contains non-finite values.")
    if any(float(value) <= 0 for value in artifact["feature_scales"]):
        raise RuntimeError("Synthetic risk model feature scales must be positive.")
    if not math.isfinite(float(artifact.get("intercept", float("nan")))):
        raise RuntimeError("Synthetic risk model intercept is not finite.")
    return artifact


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_value = math.exp(-value)
        return 1.0 / (1.0 + exp_value)
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _features(project: ProjectTelemetry) -> dict[str, float]:
    # Apply the same transformation used by the synthetic training pipeline.
    return {
        "schedule_gap_pp": max(0.0, project.planned_progress - project.actual_progress),
        "positive_budget_variance_pct": max(0.0, project.budget_variance_pct),
        "vendor_delay_days": float(project.vendor_delay_days),
        "open_issues": float(project.open_issues),
        "quality_defects": float(project.quality_defects),
    }


def assess_synthetic_risk(project: ProjectTelemetry) -> dict[str, Any]:
    """Return a screening result under synthetic label assumptions, not real risk truth."""
    model = load_model()
    features = _features(project)
    standardized = [
        (features[name] - mean) / scale
        for name, mean, scale in zip(
            model["feature_names"], model["feature_means"], model["feature_scales"]
        )
    ]
    terms = [
        float(coefficient) * float(value)
        for coefficient, value in zip(model["coefficients"], standardized)
    ]
    score = float(model["intercept"]) + sum(terms)
    synthetic_probability = _sigmoid(score)
    thresholds = model["decision_thresholds"]

    if synthetic_probability >= float(thresholds["high"]):
        band = "HIGH"
    elif synthetic_probability >= float(thresholds["watch"]):
        band = "WATCH"
    else:
        band = "LOW"

    ranked = sorted(
        zip(model["feature_names"], features.values(), model["feature_means"], terms),
        key=lambda item: item[3],
        reverse=True,
    )
    top_signals = []
    for name, value, mean, contribution in ranked:
        if contribution <= 0:
            continue
        label = DISPLAY_NAMES[name]
        if name == "schedule_gap_pp":
            unit_value = f"{value:.1f} percentage points"
            unit_mean = f"{float(mean):.1f} points"
        elif name == "positive_budget_variance_pct":
            unit_value = f"{value:.1f}%"
            unit_mean = f"{float(mean):.1f}%"
        elif name == "vendor_delay_days":
            unit_value = f"{value:.0f} days"
            unit_mean = f"{float(mean):.1f} days"
        else:
            unit_value = f"{value:.0f}"
            unit_mean = f"{float(mean):.1f}"
        top_signals.append(
            f"{label}: {unit_value}, above the synthetic training mean of {unit_mean}."
        )
        if len(top_signals) == 3:
            break
    if not top_signals:
        top_signals = [
            "No supplied feature is above its synthetic training reference in this model; "
            "this does not rule out project-specific risks the model cannot see."
        ]

    test_metrics = model["evaluation"]["test"]
    shift_metrics = model["evaluation"]["shift_stress"]
    return {
        "project_id": project.project_id,
        "model_name": model["model_name"],
        "model_version": model["model_version"],
        "model_status": model["model_status"],
        "algorithm": model["algorithm"],
        "synthetic_label_probability_pct": round(synthetic_probability * 100.0, 1),
        "risk_band": band,
        "screening_threshold_pct": round(float(thresholds["watch"]) * 100.0, 1),
        "event_definition": model["training"]["label_definition"],
        "feature_values": {name: round(value, 3) for name, value in features.items()},
        "top_signals": top_signals,
        "training_sample_count": model["training"]["train_rows"],
        "validation_sample_count": model["training"]["validation_rows"],
        "heldout_test_sample_count": model["training"]["test_rows"],
        "heldout_test_roc_auc": test_metrics["roc_auc"],
        "heldout_test_brier_score": test_metrics["brier_score"],
        "heldout_test_log_loss": test_metrics["log_loss"],
        "shift_stress_positive_rate_pct": round(float(shift_metrics["positive_rate"]) * 100.0, 1),
        "shift_stress_log_loss": shift_metrics["log_loss"],
        "warnings": [
            "EXPERIMENTAL: trained only on authored synthetic data; not trained on Prestige data.",
            "The percentage is a probability of the synthetic label under synthetic assumptions, not a calibrated probability of real project delay.",
            "A WATCH/HIGH result is a review prompt only. Expect false alerts and missed risks; do not automate decisions from this output.",
            "The input omits project type, schedule calendars, resource capacity, contract terms, weather, phase, reporting cadence and verified historical outcomes.",
        ],
        "limitations": model["limitations"],
    }


def model_metadata() -> dict[str, Any]:
    model = load_model()
    test = model["evaluation"]["test"]
    stress = model["evaluation"]["shift_stress"]
    return {
        "model_name": model["model_name"],
        "model_version": model["model_version"],
        "model_status": model["model_status"],
        "algorithm": model["algorithm"],
        "feature_names": model["feature_names"],
        "training_sample_count": model["training"]["train_rows"],
        "validation_sample_count": model["training"]["validation_rows"],
        "heldout_test_sample_count": model["training"]["test_rows"],
        "total_synthetic_rows_generated": model["training"]["total_synthetic_rows_generated"],
        "heldout_test_metrics": {
            "roc_auc": test["roc_auc"],
            "brier_score": test["brier_score"],
            "log_loss": test["log_loss"],
            "recall_at_25pct_screening_threshold": test["review_threshold_0_25"]["recall"],
            "precision_at_25pct_screening_threshold": test["review_threshold_0_25"]["precision"],
        },
        "shift_stress_metrics": {
            "positive_rate": stress["positive_rate"],
            "roc_auc": stress["roc_auc"],
            "brier_score": stress["brier_score"],
            "log_loss": stress["log_loss"],
        },
        "label_definition": model["training"]["label_definition"],
        "limitations": model["limitations"],
    }
