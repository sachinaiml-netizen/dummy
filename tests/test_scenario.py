from fastapi.testclient import TestClient

from app.decision_engine import simulate_project
from app.main import app

client = TestClient(app)


def test_default_scenario_explains_critical_path_recovery():
    result = simulate_project("ST-01", 14, 4.5)
    assert result["baseline_finish_day"] == 119
    assert result["shocked_finish_day"] == 133
    assert result["shocked_slip_days"] == 14
    assert result["recommended_action"]["id"] == "structural_recovery"
    assert result["recommended_action"]["days_recovered"] == 6
    assert result["recommended_action"]["net_value_lakh"] == 19.0
    assert result["recommended_finish_day"] == 127


def test_noncritical_procurement_delay_can_be_absorbed_by_schedule_float():
    result = simulate_project("PR-01", 14, 4.5)
    assert result["baseline_finish_day"] == 119
    assert result["shocked_finish_day"] == 119
    assert result["shocked_slip_days"] == 0
    assert result["recommended_action"]["id"] == "none"
    expedite = next(row for row in result["ranked_interventions"] if row["id"] == "supplier_expedite")
    assert expedite["days_recovered"] == 0
    assert expedite["net_value_lakh"] == -12.0


def test_zero_exposure_means_no_positive_paid_intervention_value():
    result = simulate_project("ST-01", 14, 0)
    assert result["gross_delay_exposure_lakh"] == 0
    assert result["recommended_action"]["id"] == "none"


def test_invalid_activity_is_rejected():
    try:
        simulate_project("NO-SUCH-TASK", 14, 4.5)
    except ValueError as exc:
        assert "Unknown activity" in str(exc)
    else:
        raise AssertionError("Unknown activity should fail validation.")


def test_api_health_and_scenario_work():
    assert client.get("/health").json()["status"] == "ok"
    response = client.post(
        "/api/scenario",
        json={
            "disrupted_activity_id": "ST-01",
            "delay_days": 14,
            "exposure_lakh_per_day": 4.5,
        },
    )
    assert response.status_code == 200
    assert response.json()["recommended_action"]["id"] == "structural_recovery"


def test_api_rejects_unknown_activity():
    response = client.post(
        "/api/scenario",
        json={
            "disrupted_activity_id": "NOPE",
            "delay_days": 14,
            "exposure_lakh_per_day": 4.5,
        },
    )
    assert response.status_code == 422



def test_critical_path_case_shows_stability_for_nearby_assumptions():
    result = simulate_project("ST-01", 14, 4.5)
    sensitivity = result["sensitivity"]
    assert sensitivity["tested_scenarios"] == 9
    assert sensitivity["delay_range_days"] == [10, 18]
    assert sensitivity["stable"] is True
    assert sensitivity["stability_pct"] == 100
    assert any(item["selected_trials"] > 0 for item in sensitivity["action_frequency"])


def test_float_case_can_show_a_fragile_decision_near_the_threshold():
    result = simulate_project("PR-01", 14, 4.5)
    sensitivity = result["sensitivity"]
    assert sensitivity["tested_scenarios"] == 9
    assert any(item["id"] == "none" for item in sensitivity["action_frequency"])
    assert any(item["id"] == "handover_sprint" for item in sensitivity["action_frequency"])
    assert sensitivity["stable"] is False
