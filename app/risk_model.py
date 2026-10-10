"""Inference for the small synthetic-trained risk proof model.

Keep the model artifact small and dependency-free. A score from the current
synthetic artifact is not a calibrated probability of an actual project event.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .schemas import ProjectTelemetry

MODEL_PATH = Path(__file__).resolve().with_name("risk_model.json")
FEATURE_LABELS = {
    "planned_progress_pct": "Planned progress (%)",
    "schedule_gap_pp": "Schedule gap (percentage points)",
    "positive_budget_variance_pct": "Positive budget variance (%)",
    "vendor_delay_days": "Vendor delay (days)",
    "open_issues": "Unresolved issues",
    "quality_defects": "Quality defects",
}


def _load_model() -> dict[str, Any]:
    try:
        model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Risk proof-model artifact is missing or invalid") from exc
    count = len(model.get("feature_schema", []))
    if (
        count == 0
        or len(model.get("coefficients", [])) != count
        or len(model.get("means", [])) != count
        or len(model.get("scales", [])) != count
        or any(not math.isfinite(float(value)) for value in model["coefficients"] + model["means"] + model["scales"])
        or any(float(value) <= 0 for value in model["scales"])
    ):
        raise RuntimeError("Risk proof-model artifact has an invalid feature schema or parameters")
    return model


MODEL = _load_model()


def _sigmoid(value: float) -> float:
    if value >= 35:
        return 1.0
    if value <= -35:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


def _feature_values(project: ProjectTelemetry) -> dict[str, float]:
    return {
        "planned_progress_pct": float(project.planned_progress),
        "schedule_gap_pp": max(0.0, float(project.planned_progress) - float(project.actual_progress)),
        "positive_budget_variance_pct": max(0.0, float(project.budget_variance_pct)),
        "vendor_delay_days": float(project.vendor_delay_days),
        "open_issues": float(project.open_issues),
        "quality_defects": float(project.quality_defects),
    }


def score_project(project: ProjectTelemetry) -> dict[str, Any]:
    values = _feature_values(project)
    features = MODEL["feature_schema"]
    logit = float(MODEL["intercept"])
    impacts: list[dict[str, Any]] = []
    for index, feature in enumerate(features):
        key = feature["key"]
        raw_value = values[key]
        standardized = (raw_value - float(MODEL["means"][index])) / float(MODEL["scales"][index])
        contribution = float(MODEL["coefficients"][index]) * standardized
        logit += contribution
        impacts.append({
            "feature": key,
            "label": FEATURE_LABELS.get(key, feature.get("label", key)),
            "raw_value": round(raw_value, 3),
            "standardized_value": round(standardized, 4),
            "logit_contribution": round(contribution, 4),
            "direction": "raises the synthetic-model score" if contribution > 0.00005
                else ("lowers the synthetic-model score" if contribution < -0.00005 else "little contribution"),
        })

    score_pct = round(_sigmoid(logit) * 100.0, 1)
    if score_pct >= 65:
        band = "HIGH"
    elif score_pct >= 35:
        band = "MEDIUM"
    else:
        band = "LOW"
    impacts.sort(key=lambda row: abs(row["logit_contribution"]), reverse=True)
    metadata = MODEL["training_metadata"]
    metrics = MODEL["test_metrics"]
    return {
        "project_id": project.project_id,
        "model_version": MODEL["model_version"],
        "model_type": MODEL["model_type"],
        "training_data_kind": MODEL["training_data_kind"],
        "training_rows": metadata["train_rows"],
        "score_pct": score_pct,
        "risk_band": band,
        "score_semantics": (
            "Synthetic-model score: relative fit to an invented training target, not a real-world event probability."
            if MODEL["training_data_kind"] == "synthetic"
            else "Candidate score from labelled historical data; calibration and deployment validity are not certified."
        ),
        "target_column": MODEL.get("target_column", "target_high_risk_30d"),
        "target_definition": MODEL.get("target_definition", ""),
        "top_drivers": impacts[:3],
        "feature_contributions": impacts,
        "test_metrics": {
            "test_rows": metrics["test_rows"],
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "roc_auc": metrics["roc_auc"],
            "brier_score": metrics["brier_score"],
            "majority_baseline_accuracy": metrics["majority_baseline_accuracy"],
        },
        "evaluation_scope": metadata["split_strategy"],
        "important_warning": (
            "PROOF MODEL ONLY. Trained on synthetic records and synthetic labels—not Prestige or real construction outcomes. "
            "Do not use this score to approve, reject, escalate, price, or staff a real project. Validate it against "
            "authorised historical outcomes first."
            if MODEL["training_data_kind"] == "synthetic"
            else
            "CANDIDATE MODEL ONLY. It was trained on labelled historical snapshots but is not certified for operational "
            "decisions. Confirm target definitions, temporal performance, calibration, subgroups and human review."
        ),
    }
