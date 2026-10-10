from fastapi.testclient import TestClient

from app.main import app
from app.risk_model import MODEL, score_project
from app.schemas import ProjectTelemetry

client = TestClient(app)


def telemetry(**overrides):
    values = {
        "project_id": "DEMO-SNAPSHOT",
        "planned_progress": 80,
        "actual_progress": 58,
        "budget_variance_pct": 9,
        "vendor_delay_days": 10,
        "open_issues": 12,
        "quality_defects": 5,
    }
    values.update(overrides)
    return ProjectTelemetry(**values)


def test_artifact_documents_synthetic_training_and_holdout_scope():
    assert MODEL["training_data_kind"] == "synthetic"
    assert MODEL["training_metadata"]["total_rows"] == 60000
    assert MODEL["training_metadata"]["train_rows"] == 42000
    assert MODEL["training_metadata"]["validation_rows"] == 9000
    assert MODEL["training_metadata"]["test_rows"] == 9000
    assert MODEL["test_metrics"]["roc_auc"] > 0.70
    assert MODEL["test_metrics"]["accuracy"] > MODEL["test_metrics"]["majority_baseline_accuracy"]
    assert "do not estimate performance" in MODEL["training_metadata"]["warning"]


def test_trained_model_is_bounded_explainable_and_monotonic_for_schedule_gap():
    lower_gap = score_project(telemetry(actual_progress=78))
    higher_gap = score_project(telemetry(actual_progress=35))
    assert 0 <= lower_gap["score_pct"] <= 100
    assert 0 <= higher_gap["score_pct"] <= 100
    assert higher_gap["score_pct"] > lower_gap["score_pct"]
    assert len(higher_gap["feature_contributions"]) == 6
    assert len(higher_gap["top_drivers"]) == 3
    assert all("direction" in row and "logit_contribution" in row for row in higher_gap["feature_contributions"])
    assert "PROOF MODEL ONLY" in higher_gap["important_warning"]


def test_model_endpoint_returns_score_explanation_and_synthetic_metrics():
    response = client.post("/api/risk/proof-model", json={
        "project_id": "SYNTHETIC-TEST",
        "planned_progress": 80,
        "actual_progress": 58,
        "budget_variance_pct": 9,
        "vendor_delay_days": 10,
        "open_issues": 12,
        "quality_defects": 5,
    })
    assert response.status_code == 200
    result = response.json()
    assert result["model_version"] == "synthetic-logistic-v1"
    assert result["training_data_kind"] == "synthetic"
    assert isinstance(result["score_pct"], float)
    assert result["risk_band"] in {"LOW", "MEDIUM", "HIGH"}
    assert result["test_metrics"]["test_rows"] == 9000
    assert "not a real-world event probability" in result["score_semantics"]
    assert "PROOF MODEL ONLY" in result["important_warning"]


def test_model_endpoint_preserves_input_validation():
    response = client.post("/api/risk/proof-model", json={
        "project_id": "BAD",
        "planned_progress": 101,
        "actual_progress": 50,
        "budget_variance_pct": 0,
        "vendor_delay_days": 0,
        "open_issues": 0,
        "quality_defects": 0,
    })
    assert response.status_code == 422


def test_training_generator_is_seed_reproducible_and_split_is_disjoint():
    from scripts.train_risk_model import generate_synthetic_dataset, split_synthetic_indices

    x1, y1 = generate_synthetic_dataset(500, 42)
    x2, y2 = generate_synthetic_dataset(500, 42)
    assert x1 == x2 and y1 == y2
    train, validation, test = split_synthetic_indices(500, 42)
    assert len(train) == 350
    assert len(validation) == 75
    assert len(test) == 75
    assert not (set(train) & set(validation))
    assert not (set(train) & set(test))
    assert not (set(validation) & set(test))
