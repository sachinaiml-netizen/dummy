from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

from .schemas import ProjectTelemetry


def _features(p: ProjectTelemetry) -> np.ndarray:
    schedule_gap = max(0.0, p.planned_progress - p.actual_progress)
    return np.array(
        [[
            schedule_gap,
            max(0.0, p.budget_variance_pct),
            float(p.vendor_delay_days),
            float(p.open_issues),
            float(p.quality_defects),
        ]],
        dtype=float,
    )


def _risk_score(p: ProjectTelemetry) -> float:
    schedule_gap = max(0.0, p.planned_progress - p.actual_progress)

    schedule_component = min(35.0, schedule_gap * 1.8)
    cost_component = min(25.0, max(0.0, p.budget_variance_pct) * 1.25)
    vendor_component = min(15.0, p.vendor_delay_days * 1.5)
    issue_component = min(15.0, p.open_issues * 0.75)
    quality_component = min(10.0, p.quality_defects * 0.8)

    return round(
        min(
            100.0,
            schedule_component
            + cost_component
            + vendor_component
            + issue_component
            + quality_component,
        ),
        2,
    )


def _fit_reference_model() -> IsolationForest:
    rng = np.random.default_rng(42)
    # Synthetic "normal" project telemetry.
    normal = np.column_stack(
        [
            rng.normal(3, 2, 120).clip(0),
            rng.normal(2, 2, 120).clip(0),
            rng.normal(2, 2, 120).clip(0),
            rng.normal(4, 2, 120).clip(0),
            rng.normal(2, 1.5, 120).clip(0),
        ]
    )
    model = IsolationForest(n_estimators=150, contamination=0.08, random_state=42)
    model.fit(normal)
    return model


_MODEL = _fit_reference_model()


def assess_risk(project: ProjectTelemetry) -> dict:
    features = _features(project)
    # decision_function is higher for more normal observations.
    raw = float(_MODEL.decision_function(features)[0])
    anomaly_score = round(float(np.clip(0.5 - raw, 0.0, 1.0)), 3)

    score = _risk_score(project)
    if anomaly_score > 0.65:
        score = min(100.0, score + 8.0)

    if score >= 70:
        band = "HIGH"
    elif score >= 40:
        band = "MEDIUM"
    else:
        band = "LOW"

    indicators: list[str] = []
    schedule_gap = project.planned_progress - project.actual_progress

    if schedule_gap >= 8:
        indicators.append(f"{schedule_gap:.0f} percentage-point schedule gap")
    if project.budget_variance_pct >= 5:
        indicators.append("Budget variance above 5%")
    if project.vendor_delay_days >= 7:
        indicators.append("Vendor delay exceeds one week")
    if project.open_issues >= 10:
        indicators.append("High unresolved-issue count")
    if project.quality_defects >= 5:
        indicators.append("Elevated quality-defect count")
    if not indicators:
        indicators.append("No dominant leading indicator detected")

    if band == "HIGH":
        action = "Escalate a recovery plan and review the largest schedule, vendor and cost dependencies."
    elif band == "MEDIUM":
        action = "Assign an owner to the leading indicators and review the project again within 48 hours."
    else:
        action = "Continue normal monitoring and refresh the telemetry at the next reporting cycle."

    return {
        "risk_score": score,
        "risk_band": band,
        "anomaly_score": anomaly_score,
        "leading_indicators": indicators,
        "recommended_action": action,
    }
