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



def test_deviation_indicator_is_bounded_and_monotonic():
    from app.risk import _deviation_indicator
    from app.schemas import ProjectTelemetry

    low = ProjectTelemetry(
        project_id="LOW",
        planned_progress=50,
        actual_progress=49,
        budget_variance_pct=1,
        vendor_delay_days=0,
        open_issues=1,
        quality_defects=0,
    )
    high = ProjectTelemetry(
        project_id="HIGH",
        planned_progress=80,
        actual_progress=55,
        budget_variance_pct=12,
        vendor_delay_days=14,
        open_issues=20,
        quality_defects=10,
    )
    low_score = _deviation_indicator(low)
    high_score = _deviation_indicator(high)
    assert 0 <= low_score <= 1
    assert 0 <= high_score <= 1
    assert high_score > low_score
    assert high_score == 0.96


def test_risk_endpoint_keeps_legacy_response_shape_without_ml_dependencies():
    from app.risk import assess_risk
    from app.schemas import ProjectTelemetry

    project = ProjectTelemetry(
        project_id="BOUNDARY",
        planned_progress=80,
        actual_progress=55,
        budget_variance_pct=12,
        vendor_delay_days=14,
        open_issues=20,
        quality_defects=10,
    )
    result = assess_risk(project)
    assert set(result) == {
        "risk_score", "risk_band", "anomaly_score",
        "leading_indicators", "recommended_action"
    }
    assert result["risk_band"] == "HIGH"
    assert result["anomaly_score"] == 0.96
