"""Lightweight inference for Project Impact Lab's compact delay-risk model.

The FastAPI runtime uses only Python's standard library. scikit-learn is required
for offline training, not for production inference.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from .risk_features import (
    ALL_INPUT_FIELDS, FEATURE_LABELS, FEATURE_NAMES, OPTIONAL_INPUT_FIELDS, feature_values,
)

MODEL_PATH = Path(__file__).resolve().parent / "models" / "synthetic_delay_risk_v1.json"


def _load_artifact() -> dict[str, Any]:
    artifact = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    count = len(FEATURE_NAMES)
    for key in ("scaler_mean", "scaler_scale", "coefficients"):
        if len(artifact.get(key, [])) != count:
            raise RuntimeError(f"Risk model artifact {key} length does not match feature schema")
    if artifact.get("feature_names") != FEATURE_NAMES:
        raise RuntimeError("Risk model artifact feature order does not match runtime feature engineering")
    if any(not math.isfinite(float(v)) for key in ("scaler_mean", "scaler_scale", "coefficients") for v in artifact[key]):
        raise RuntimeError("Risk model artifact contains a non-finite value")
    if any(float(v) <= 0 for v in artifact["scaler_scale"]):
        raise RuntimeError("Risk model artifact scaler contains a non-positive scale")
    return artifact


MODEL = _load_artifact()


def _raw_input_ranges(snapshot: Mapping[str, Any]) -> list[str]:
    """Report inputs outside the ranges represented in this model's training data."""
    ranges = MODEL.get("input_support_ranges", MODEL.get("synthetic_input_ranges", {}))
    out: list[str] = []
    for field, bounds in ranges.items():
        value = snapshot.get(field)
        if value is None:
            continue
        if field == "phase":
            if str(value).lower().strip() not in bounds:
                out.append(field)
        else:
            number = float(value)
            if number < float(bounds[0]) or number > float(bounds[1]):
                out.append(field)
    return out


def predict_delay_risk(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Score a snapshot, withholding scores for sparse or out-of-support inputs.

    A score from the synthetic model is not a calibrated probability for a real
    project. The API reports the scope and limits with every response.
    """
    missing = [field for field in OPTIONAL_INPUT_FIELDS if snapshot.get(field) is None]
    coverage = 100.0 * (len(ALL_INPUT_FIELDS) - len(missing)) / len(ALL_INPUT_FIELDS)
    out_of_range = _raw_input_ranges(snapshot)
    score_available = coverage >= 75.0 and not out_of_range

    probability: float | None = None
    band: str | None = None
    drivers: list[dict[str, Any]] = []
    if score_available:
        values = feature_values(snapshot)
        standardized = [
            (float(value) - float(mean)) / float(scale)
            for value, mean, scale in zip(values, MODEL["scaler_mean"], MODEL["scaler_scale"])
        ]
        logit = float(MODEL["intercept"]) + sum(
            float(coefficient) * value
            for coefficient, value in zip(MODEL["coefficients"], standardized)
        )
        logit = max(-30.0, min(30.0, logit))
        probability = 1.0 / (1.0 + math.exp(-logit))
        thresholds = MODEL["risk_band_thresholds"]
        if probability >= float(thresholds["high_at_or_above"]):
            band = "HIGH"
        elif probability >= float(thresholds["medium_at_or_above"]):
            band = "MEDIUM"
        else:
            band = "LOW"

        # These are additive model associations, not causal explanations.
        contributions = []
        for name, coefficient, z_score in zip(FEATURE_NAMES, MODEL["coefficients"], standardized):
            coefficient = float(coefficient)
            contribution = coefficient * z_score
            if coefficient > 0 and z_score > 0 and contribution > .015 and name in FEATURE_LABELS:
                contributions.append({
                    "feature": name,
                    "label": FEATURE_LABELS[name],
                    "contribution_log_odds": round(contribution, 3),
                })
        contributions.sort(key=lambda row: row["contribution_log_odds"], reverse=True)
        drivers = contributions[:5]

    model_source = MODEL.get("data_source", "unknown")
    synthetic_only = model_source == "synthetic_generator"
    stage = "synthetic_research_prototype" if synthetic_only else "labelled_data_pilot_model"
    evaluation_scope = "synthetic_holdout_only" if synthetic_only else "project_group_holdout_from_supplied_labelled_data"
    if out_of_range:
        status = "SCORE_WITHHELD_OUTSIDE_TRAINING_SUPPORT"
    elif coverage < 75.0:
        status = "SCORE_WITHHELD_INSUFFICIENT_INPUT_COVERAGE"
    else:
        status = "SYNTHETIC_ONLY_NOT_REAL_WORLD_VALIDATED" if synthetic_only else "PILOT_MODEL_REQUIRES_HUMAN_REVIEW"

    metrics = MODEL.get("test_metrics", {})
    return {
        "project_id": str(snapshot["project_id"]),
        "model_name": MODEL["model_name"],
        "model_version": MODEL["model_version"],
        "model_stage": stage,
        "target": MODEL["task"],
        "target_definition": MODEL["target_definition"],
        "score_available": score_available,
        "synthetic_model_probability_pct": round(probability * 100.0, 1) if probability is not None else None,
        "risk_band": band,
        "risk_band_thresholds": MODEL["risk_band_thresholds"],
        "data_completeness_pct": round(coverage, 1),
        "missing_optional_fields": missing,
        "out_of_training_range_fields": out_of_range,
        "reliability_status": status,
        "top_model_contributors": drivers,
        "evaluation_scope": evaluation_scope,
        "dataset_rows": int(MODEL["dataset_rows"]),
        "split_rows": MODEL["split_rows"],
        "split_project_counts": MODEL.get("split_project_counts", {}),
        "test_metrics": metrics,
        "model_limitations": MODEL.get("limitations", []),
        "interpretation_warning": (
            "This is a generated-data research score, not a Prestige-specific probability or a safe basis for approving schedule, cost, safety, or recovery decisions."
            if synthetic_only else
            "This model uses supplied labelled data but is still a pilot; check project-level holdout performance, calibration, sample size and drift before operational use."
        ),
    }


def risk_model_info() -> dict[str, Any]:
    """Return model metadata and holdout metrics for the dashboard/API."""
    source = MODEL.get("data_source", "unknown")
    return {
        "model_name": MODEL["model_name"],
        "model_version": MODEL["model_version"],
        "model_type": MODEL["model_type"],
        "model_stage": "synthetic_research_prototype" if source == "synthetic_generator" else "labelled_data_pilot_model",
        "data_source": source,
        "target": MODEL["task"],
        "target_definition": MODEL["target_definition"],
        "dataset_rows": int(MODEL["dataset_rows"]),
        "split_rows": MODEL["split_rows"],
        "split_project_counts": MODEL.get("split_project_counts", {}),
        "test_metrics": MODEL.get("test_metrics", {}),
        "risk_band_thresholds": MODEL["risk_band_thresholds"],
        "feature_count": len(FEATURE_NAMES),
        "limitations": MODEL.get("limitations", []),
    }
