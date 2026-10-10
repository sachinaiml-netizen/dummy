from fastapi.testclient import TestClient

from app.main import app
from app.ml_risk import assess_synthetic_risk, load_model
from app.schemas import ProjectTelemetry

client = TestClient(app)


def telemetry(project_id, planned, actual, budget, vendor, issues, defects):
    return ProjectTelemetry(
        project_id=project_id,
        planned_progress=planned,
        actual_progress=actual,
        budget_variance_pct=budget,
        vendor_delay_days=vendor,
        open_issues=issues,
        quality_defects=defects,
    )


def test_model_artifact_is_versioned_and_explicitly_synthetic():
    model = load_model()
    assert model["model_version"] == "0.1.0-synthetic"
    assert model["model_status"] == "EXPERIMENTAL_SYNTHETIC_ONLY"
    assert model["training"]["train_rows"] == 70_000
    assert model["training"]["validation_rows"] == 15_000
    assert model["training"]["test_rows"] == 15_000
    assert model["training"]["shift_stress_rows"] == 15_000
    assert model["training"]["total_synthetic_rows_generated"] == 115_000
    assert "not an observed construction outcome" in model["training"]["label_definition"]


def test_model_flags_higher_synthetic_signals_more_strongly_than_healthy_snapshot():
    healthy = telemetry("HEALTHY", 50, 49, 1, 0, 1, 0)
    stressed = telemetry("STRESSED", 80, 55, 12, 14, 20, 10)

    low = assess_synthetic_risk(healthy)
    high = assess_synthetic_risk(stressed)

    assert 0 <= low["synthetic_label_probability_pct"] <= 100
    assert 0 <= high["synthetic_label_probability_pct"] <= 100
    assert high["synthetic_label_probability_pct"] > low["synthetic_label_probability_pct"]
    assert high["risk_band"] == "HIGH"
    assert low["risk_band"] == "LOW"
    assert high["model_status"] == "EXPERIMENTAL_SYNTHETIC_ONLY"
    assert high["training_sample_count"] == 70_000
    assert high["heldout_test_sample_count"] == 15_000
    assert len(high["top_signals"]) > 0
    assert any("not a calibrated probability" in warning for warning in high["warnings"])


def test_model_api_returns_metrics_limitations_and_probabilistic_label_semantics():
    response = client.post(
        "/risk-model",
        json={
            "project_id": "API-SYNTHETIC-TEST",
            "planned_progress": 80,
            "actual_progress": 55,
            "budget_variance_pct": 12,
            "vendor_delay_days": 14,
            "open_issues": 20,
            "quality_defects": 10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "0.1.0-synthetic"
    assert body["synthetic_label_probability_pct"] > 90
    assert body["risk_band"] == "HIGH"
    assert body["heldout_test_roc_auc"] == 0.800235
    assert body["heldout_test_brier_score"] == 0.141409
    assert body["shift_stress_positive_rate_pct"] == 55.6
    assert any("synthetic label" in warning for warning in body["warnings"])
    assert len(body["limitations"]) >= 5


def test_model_metadata_route_distinguishes_iid_test_from_shift_stress():
    response = client.get("/risk-model/info")
    assert response.status_code == 200
    body = response.json()
    assert body["model_status"] == "EXPERIMENTAL_SYNTHETIC_ONLY"
    assert body["total_synthetic_rows_generated"] == 115_000
    assert body["heldout_test_metrics"]["roc_auc"] == 0.800235
    assert body["shift_stress_metrics"]["positive_rate"] == 0.556267
    assert body["shift_stress_metrics"]["log_loss"] > body["heldout_test_metrics"]["log_loss"]


def test_model_endpoint_rejects_invalid_telemetry():
    response = client.post(
        "/risk-model",
        json={
            "project_id": "BAD",
            "planned_progress": 140,
            "actual_progress": 20,
            "budget_variance_pct": 0,
            "vendor_delay_days": 0,
            "open_issues": 0,
            "quality_defects": 0,
        },
    )
    assert response.status_code == 422
