from fastapi.testclient import TestClient

from app.main import app
from app.risk_model import predict_delay_risk, risk_model_info

client = TestClient(app)


def snapshot(**overrides):
    base = {
        "project_id": "SYNTHETIC-TEST",
        "planned_progress": 65,
        "actual_progress": 54,
        "budget_variance_pct": 8,
        "vendor_delay_days": 14,
        "open_issues": 12,
        "quality_defects": 4,
        "total_float_days": 7,
        "float_consumed_pct": 78,
        "procurement_delay_days": 12,
        "long_lead_items_at_risk": 3,
        "approval_overdue_days": 9,
        "labour_shortage_pct": 25,
        "weather_lost_days_30d": 3,
        "design_changes_30d": 2,
        "safety_actions_overdue": 2,
        "phase": "structure",
    }
    base.update(overrides)
    return base


def test_model_artifact_and_metrics_are_present_and_scoped_to_holdout():
    info = risk_model_info()
    assert info["model_type"] == "standardized_logistic_regression"
    assert info["data_source"] == "synthetic_generator"
    assert info["dataset_rows"] == 50000
    assert info["split_rows"] == {"train": 35000, "validation": 7500, "test": 7500}
    assert info["split_project_counts"] == {"train": 35000, "validation": 7500, "test": 7500}
    assert info["feature_count"] == 30
    assert info["test_metrics"]["roc_auc"] >= 0.78
    assert info["test_metrics"]["brier_skill_vs_prevalence_baseline"] > 0.20


def test_api_risk_prediction_returns_synthetic_disclosure_and_contributors():
    response = client.post("/api/risk/predict", json=snapshot())
    assert response.status_code == 200
    data = response.json()
    assert data["score_available"] is True
    assert data["data_completeness_pct"] == 100
    assert 0 <= data["synthetic_model_probability_pct"] <= 100
    assert data["risk_band"] in {"LOW", "MEDIUM", "HIGH"}
    assert data["model_stage"] == "synthetic_research_prototype"
    assert data["reliability_status"] == "SYNTHETIC_ONLY_NOT_REAL_WORLD_VALIDATED"
    assert data["evaluation_scope"] == "synthetic_holdout_only"
    assert data["test_metrics"]["roc_auc"] >= 0.78
    assert "not a Prestige-specific probability" in data["interpretation_warning"]


def test_model_ranks_clearer_synthetic_risk_snapshots_higher():
    low = snapshot(
        project_id="SYN-LOW", planned_progress=50, actual_progress=49,
        budget_variance_pct=0, vendor_delay_days=0, open_issues=0, quality_defects=0,
        total_float_days=60, float_consumed_pct=5, procurement_delay_days=0,
        long_lead_items_at_risk=0, approval_overdue_days=0, labour_shortage_pct=0,
        weather_lost_days_30d=0, design_changes_30d=0, safety_actions_overdue=0,
        phase="design",
    )
    high = snapshot(
        project_id="SYN-HIGH", planned_progress=85, actual_progress=48,
        budget_variance_pct=35, vendor_delay_days=50, open_issues=45, quality_defects=25,
        total_float_days=-10, float_consumed_pct=150, procurement_delay_days=50,
        long_lead_items_at_risk=25, approval_overdue_days=45, labour_shortage_pct=70,
        weather_lost_days_30d=10, design_changes_30d=18, safety_actions_overdue=15,
        phase="structure",
    )
    low_result = predict_delay_risk(low)
    high_result = predict_delay_risk(high)
    assert low_result["score_available"] is True
    assert high_result["score_available"] is True
    assert high_result["synthetic_model_probability_pct"] > low_result["synthetic_model_probability_pct"]
    assert high_result["risk_band"] == "HIGH"
    assert high_result["top_model_contributors"]


def test_model_withholds_score_when_optional_input_coverage_is_too_low():
    response = client.post("/api/risk/predict", json={
        "project_id": "MISSING-SIGNALS", "planned_progress": 60, "actual_progress": 53,
        "budget_variance_pct": 4, "vendor_delay_days": 3, "open_issues": 3, "quality_defects": 1,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["score_available"] is False
    assert data["synthetic_model_probability_pct"] is None
    assert data["risk_band"] is None
    assert data["data_completeness_pct"] == 37.5
    assert len(data["missing_optional_fields"]) == 10
    assert data["reliability_status"] == "SCORE_WITHHELD_INSUFFICIENT_INPUT_COVERAGE"


def test_model_withholds_score_for_values_outside_training_support():
    data = snapshot(budget_variance_pct=120)
    result = predict_delay_risk(data)
    assert result["score_available"] is False
    assert result["synthetic_model_probability_pct"] is None
    assert "budget_variance_pct" in result["out_of_training_range_fields"]
    assert result["reliability_status"] == "SCORE_WITHHELD_OUTSIDE_TRAINING_SUPPORT"


def test_invalid_phase_is_rejected_by_request_validation():
    data = snapshot(phase="unknown-phase")
    response = client.post("/api/risk/predict", json=data)
    assert response.status_code == 422


def test_existing_rule_based_risk_endpoint_remains_backward_compatible():
    response = client.post("/risk", json={
        "project_id": "LEGACY", "planned_progress": 80, "actual_progress": 55,
        "budget_variance_pct": 12, "vendor_delay_days": 14, "open_issues": 20,
        "quality_defects": 10,
    })
    assert response.status_code == 200
    assert set(response.json()) == {
        "project_id", "risk_score", "risk_band", "anomaly_score",
        "leading_indicators", "recommended_action",
    }


def test_model_info_endpoint_documents_training_size_and_test_metrics():
    response = client.get("/api/risk/model-info")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_rows"] == 50000
    assert data["test_metrics"]["roc_auc"] >= 0.78
    assert "Risk percentages are not calibrated" in " ".join(data["limitations"])
