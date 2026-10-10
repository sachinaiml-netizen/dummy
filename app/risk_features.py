"""Shared, dependency-light feature engineering for Project Impact Lab's risk model."""
from __future__ import annotations

from typing import Any, Mapping

FEATURE_NAMES = [
    "planned_progress_pct", "actual_progress_pct", "schedule_gap_pp",
    "budget_variance_pct", "vendor_delay_days", "open_issues", "quality_defects",
    "total_float_days", "float_consumed_pct", "procurement_delay_days",
    "long_lead_items_at_risk", "approval_overdue_days", "labour_shortage_pct",
    "weather_lost_days_30d", "design_changes_30d", "safety_actions_overdue",
    "phase_design", "phase_structure", "phase_envelope", "phase_finishes",
    "phase_commissioning", "low_float_pressure", "procurement_pressure",
    "approval_phase_pressure", "quality_closeout_pressure", "labour_site_pressure",
    "weather_site_pressure", "design_change_phase_pressure", "float_burn_pressure",
    "vendor_schedule_interaction",
]

PHASES = ("design", "structure", "envelope", "finishes", "commissioning")

# Reference imputations are illustrative fallbacks, not real-project medians.
IMPUTE_DEFAULTS = {
    "total_float_days": 15.0,
    "float_consumed_pct": 30.0,
    "procurement_delay_days": 4.0,
    "long_lead_items_at_risk": 2.0,
    "approval_overdue_days": 5.0,
    "labour_shortage_pct": 20.0,
    "weather_lost_days_30d": 2.0,
    "design_changes_30d": 3.0,
    "safety_actions_overdue": 1.0,
}
OPTIONAL_INPUT_FIELDS = tuple(IMPUTE_DEFAULTS) + ("phase",)
ALL_INPUT_FIELDS = (
    "planned_progress", "actual_progress", "budget_variance_pct", "vendor_delay_days",
    "open_issues", "quality_defects", *OPTIONAL_INPUT_FIELDS,
)

FEATURE_LABELS = {
    "schedule_gap_pp": "Gap between planned and actual progress",
    "budget_variance_pct": "Budget overrun versus plan",
    "vendor_delay_days": "Vendor delay",
    "open_issues": "Unresolved issues",
    "quality_defects": "Quality defects",
    "total_float_days": "Remaining total float",
    "float_consumed_pct": "Baseline float consumed",
    "procurement_delay_days": "Procurement delay",
    "long_lead_items_at_risk": "Long-lead items at risk",
    "approval_overdue_days": "Overdue approvals",
    "labour_shortage_pct": "Labour shortage",
    "weather_lost_days_30d": "Weather-related lost days",
    "design_changes_30d": "Recent design changes",
    "safety_actions_overdue": "Overdue safety actions",
    "low_float_pressure": "Low or negative float pressure",
    "procurement_pressure": "Procurement delay × long-lead exposure",
    "approval_phase_pressure": "Overdue approvals during design/structure",
    "quality_closeout_pressure": "Quality issues during finishes/commissioning",
    "labour_site_pressure": "Labour shortage during site work",
    "weather_site_pressure": "Weather disruption during site work",
    "design_change_phase_pressure": "Design changes during design/structure",
    "float_burn_pressure": "Float consumption with low float remaining",
    "vendor_schedule_interaction": "Vendor delay combined with schedule slippage",
}


def feature_values(snapshot: Mapping[str, Any]) -> list[float]:
    """Build the trained model's feature vector in FEATURE_NAMES order."""
    def value(name: str) -> float:
        raw = snapshot.get(name)
        if raw is None:
            raw = IMPUTE_DEFAULTS[name]
        return float(raw)

    planned = float(snapshot["planned_progress"])
    actual = float(snapshot["actual_progress"])
    budget = float(snapshot["budget_variance_pct"])
    vendor = float(snapshot["vendor_delay_days"])
    issues = float(snapshot["open_issues"])
    defects = float(snapshot["quality_defects"])
    total_float = value("total_float_days")
    float_consumed = value("float_consumed_pct")
    procurement = value("procurement_delay_days")
    long_lead = value("long_lead_items_at_risk")
    approvals = value("approval_overdue_days")
    labour = value("labour_shortage_pct")
    weather = value("weather_lost_days_30d")
    changes = value("design_changes_30d")
    safety = value("safety_actions_overdue")

    phase = snapshot.get("phase")
    phase = phase.lower().strip() if isinstance(phase, str) else None
    is_design = float(phase == "design")
    is_structure = float(phase == "structure")
    is_envelope = float(phase == "envelope")
    is_finishes = float(phase == "finishes")
    is_commissioning = float(phase == "commissioning")
    early_phase = float(phase in ("design", "structure"))
    site_phase = float(phase in ("structure", "envelope", "finishes"))
    closeout_phase = float(phase in ("finishes", "commissioning"))
    gap = max(planned - actual, 0.0)

    return [
        planned, actual, gap, budget, vendor, issues, defects, total_float,
        float_consumed, procurement, long_lead, approvals, labour, weather, changes, safety,
        is_design, is_structure, is_envelope, is_finishes, is_commissioning,
        max(0.0, 15.0 - total_float),
        (procurement / 30.0) * (long_lead / 10.0),
        (approvals / 30.0) * early_phase,
        (defects / 15.0) * closeout_phase,
        (labour / 100.0) * site_phase,
        (weather / 15.0) * site_phase,
        (changes / 15.0) * (is_design + is_structure),
        (float_consumed / 100.0) * (max(0.0, 15.0 - total_float) / 15.0),
        (vendor / 30.0) * (gap / 20.0),
    ]
