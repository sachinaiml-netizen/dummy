from app.main import risk
from app.schemas import ProjectTelemetry


def test_high_risk_project_is_flagged():
    project = ProjectTelemetry(
        project_id="TEST-HIGH",
        planned_progress=80,
        actual_progress=55,
        budget_variance_pct=12,
        vendor_delay_days=14,
        open_issues=20,
        quality_defects=10,
    )
    result = risk(project)
    assert result.risk_band == "HIGH"
    assert result.risk_score >= 70


def test_healthy_project_is_not_high_risk():
    project = ProjectTelemetry(
        project_id="TEST-LOW",
        planned_progress=50,
        actual_progress=49,
        budget_variance_pct=1,
        vendor_delay_days=0,
        open_issues=1,
        quality_defects=0,
    )
    result = risk(project)
    assert result.risk_band in {"LOW", "MEDIUM"}
