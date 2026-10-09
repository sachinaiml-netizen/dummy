from __future__ import annotations

from .schemas import ProjectTelemetry


def _risk_score(project: ProjectTelemetry) -> float:
    """Transparent weighted snapshot score; weights are illustrative, not calibrated."""
    schedule_gap = max(0.0, project.planned_progress - project.actual_progress)
    schedule_component = min(35.0, schedule_gap * 1.8)
    cost_component = min(25.0, max(0.0, project.budget_variance_pct) * 1.25)
    vendor_component = min(15.0, project.vendor_delay_days * 1.5)
    issue_component = min(15.0, project.open_issues * 0.75)
    quality_component = min(10.0, project.quality_defects * 0.8)

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


def _deviation_indicator(project: ProjectTelemetry) -> float:
    """Bounded rule-based deviation index, retained under the legacy API field name.

    This is not an Isolation Forest, trained anomaly detector, or probability.
    Each signal is normalized against a documented illustrative reference range,
    capped at 1, and combined with fixed weights that sum to 1.
    """
    schedule_gap = max(0.0, project.planned_progress - project.actual_progress)
    components = (
        (min(schedule_gap / 20.0, 1.0), 0.25),
        (min(max(project.budget_variance_pct, 0.0) / 15.0, 1.0), 0.20),
        (min(project.vendor_delay_days / 14.0, 1.0), 0.20),
        (min(project.open_issues / 20.0, 1.0), 0.20),
        (min(project.quality_defects / 10.0, 1.0), 0.15),
    )
    return round(sum(signal * weight for signal, weight in components), 3)


def assess_risk(project: ProjectTelemetry) -> dict:
    deviation_score = _deviation_indicator(project)
    score = _risk_score(project)
    if deviation_score > 0.65:
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
        # Kept for response compatibility; the value is heuristic, not a probability.
        "anomaly_score": deviation_score,
        "leading_indicators": indicators,
        "recommended_action": action,
    }
