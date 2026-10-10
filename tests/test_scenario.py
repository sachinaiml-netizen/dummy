from fastapi.testclient import TestClient

from app.decision_engine import analyze_schedule, simulate_project
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


def test_browser_dashboard_is_served_by_fastapi():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Project Impact Lab" in response.text


def test_vercel_config_includes_runtime_dashboard_asset():
    import json
    from pathlib import Path

    config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))
    assert config["framework"] == "fastapi"
    assert config["functions"]["app/main.py"]["includeFiles"] == "static/**"



def test_baseline_schedule_reports_float_for_near_critical_activities():
    result = simulate_project("PR-01", 14, 4.5)
    activities = {item["id"]: item for item in result["activities"]}
    assert activities["ST-01"]["baseline_total_float_days"] == 0
    assert activities["FC-01"]["baseline_total_float_days"] == 0
    assert activities["ME-01"]["baseline_total_float_days"] == 6
    assert activities["PR-01"]["baseline_total_float_days"] == 15
    assert result["baseline_critical_path_count"] == 1


def test_analyzer_accepts_unsorted_tasks_and_preserves_tied_critical_paths():
    tasks = [
        {"id": "finish", "duration": 1, "predecessors": ["left", "right"]},
        {"id": "right", "duration": 4, "predecessors": []},
        {"id": "short", "duration": 1, "predecessors": []},
        {"id": "left", "duration": 4, "predecessors": []},
    ]
    result = analyze_schedule(tasks)
    assert result["project_finish"] == 5
    assert result["critical_path_count"] == 2
    assert result["critical_paths"] == [["right", "finish"], ["left", "finish"]]
    assert result["total_float"]["short"] == 4
    assert result["topological_order"].index("finish") > result["topological_order"].index("left")
    assert result["topological_order"].index("finish") > result["topological_order"].index("right")


def test_analyzer_reports_multiple_terminal_activities_against_shared_project_finish():
    tasks = [
        {"id": "critical", "duration": 8, "predecessors": []},
        {"id": "short", "duration": 3, "predecessors": []},
    ]
    result = analyze_schedule(tasks)
    assert result["project_finish"] == 8
    assert result["critical_paths"] == [["critical"]]
    assert result["total_float"]["critical"] == 0
    assert result["total_float"]["short"] == 5


def test_analyzer_rejects_unknown_predecessor():
    tasks = [{"id": "A", "duration": 2, "predecessors": ["MISSING"]}]
    try:
        analyze_schedule(tasks)
    except ValueError as exc:
        assert "Unknown predecessor" in str(exc)
    else:
        raise AssertionError("Unknown predecessor should be rejected")


def test_analyzer_rejects_dependency_cycles():
    tasks = [
        {"id": "A", "duration": 2, "predecessors": ["B"]},
        {"id": "B", "duration": 3, "predecessors": ["A"]},
    ]
    try:
        analyze_schedule(tasks)
    except ValueError as exc:
        assert "Dependency cycle detected" in str(exc)
    else:
        raise AssertionError("A cyclic dependency graph should be rejected")


def test_analyzer_rejects_duplicate_ids_and_non_positive_duration():
    try:
        analyze_schedule([
            {"id": "A", "duration": 1, "predecessors": []},
            {"id": "A", "duration": 2, "predecessors": []},
        ])
    except ValueError as exc:
        assert "Duplicate task id" in str(exc)
    else:
        raise AssertionError("Duplicate task IDs should be rejected")

    try:
        analyze_schedule([{"id": "A", "duration": 0, "predecessors": []}])
    except ValueError as exc:
        assert "positive finite number" in str(exc)
    else:
        raise AssertionError("Zero duration should be rejected")


def test_analyzer_bounds_materialized_critical_paths_but_reports_exact_count():
    tasks = [
        {"id": "merge2", "duration": 1, "predecessors": ["left2", "right2"]},
        {"id": "left2", "duration": 1, "predecessors": ["left1", "right1"]},
        {"id": "right2", "duration": 1, "predecessors": ["left1", "right1"]},
        {"id": "left1", "duration": 1, "predecessors": ["start"]},
        {"id": "right1", "duration": 1, "predecessors": ["start"]},
        {"id": "start", "duration": 1, "predecessors": []},
    ]
    result = analyze_schedule(tasks, max_paths_to_return=1)
    assert result["critical_path_count"] == 4
    assert len(result["critical_paths"]) == 1
    assert result["critical_paths_truncated"] is True



def test_procurement_delay_exhausting_float_exposes_tied_critical_paths():
    result = simulate_project("PR-01", 15, 4.5)
    assert result["baseline_finish_day"] == 119
    assert result["shocked_finish_day"] == 119
    assert result["shocked_slip_days"] == 0
    assert result["shocked_critical_path_count"] == 2
    path_set = {tuple(path) for path in result["shocked_critical_paths"]}
    assert ("AP-01", "DS-01", "ST-01", "FC-01", "IN-01", "HO-01") in path_set
    assert ("AP-01", "DS-01", "PR-01", "ME-01", "IN-01", "HO-01") in path_set
    activities = {item["id"]: item for item in result["activities"]}
    assert activities["PR-01"]["shocked_total_float_days"] == 0
    assert activities["ME-01"]["shocked_total_float_days"] == 0


def test_api_default_scenario_matches_the_float_burn_problem_statement():
    response = client.get("/api/scenario")
    assert response.status_code == 200
    data = response.json()
    assert data["disrupted_activity_id"] == "PR-01"
    assert data["delay_days"] == 14
    assert data["baseline_finish_day"] == 119
    assert data["shocked_finish_day"] == 119
    assert data["shocked_slip_days"] == 0
    assert data["disrupted_activity_baseline_total_float_days"] == 15
    assert data["disrupted_activity_scenario_total_float_days"] == 1
    assert data["disrupted_activity_float_consumed_days"] == 14
    assert data["recommended_action"]["id"] == "none"
    procurement = next(item for item in data["activities"] if item["id"] == "PR-01")
    assert procurement["baseline_total_float_days"] == 15
    assert procurement["shocked_total_float_days"] == 1


def test_dashboard_defaults_to_the_same_procurement_threshold_scenario():
    response = client.get("/")
    assert response.status_code == 200
    page = response.text
    assert "activitySelect.value = catalog.activities.some(function(task){return task.id==='PR-01';})" in page
    assert 'id="float14Case"' in page
    assert "Procurement has 15 days" not in page  # copy uses lower-case 'procurement'; no case-sensitive mismatch



def test_analyzer_handles_a_long_valid_chain_without_recursion_failure():
    tasks = [
        {
            "id": f"T{index}",
            "duration": 1,
            "predecessors": [f"T{index - 1}"] if index else [],
        }
        for index in range(1200)
    ]
    result = analyze_schedule(tasks)
    assert result["project_finish"] == 1200
    assert result["critical_path_count"] == 1
    assert len(result["critical_paths"][0]) == 1200
    assert result["total_float"]["T600"] == 0


def test_analyzer_rejects_surrounding_whitespace_in_ids_and_invalid_override_shape():
    try:
        analyze_schedule([{"id": " A ", "duration": 1, "predecessors": []}])
    except ValueError as exc:
        assert "surrounding whitespace" in str(exc)
    else:
        raise AssertionError("Padded task IDs should be rejected")

    try:
        analyze_schedule([{"id": "A", "duration": 1, "predecessors": []}], duration_overrides=[])
    except ValueError as exc:
        assert "duration_overrides must be a dictionary" in str(exc)
    else:
        raise AssertionError("An invalid duration override container should be rejected")



def test_near_critical_procurement_delay_explains_remaining_float_before_handover_moves():
    result = simulate_project("PR-01", 14, 4.5)
    assert result["baseline_finish_day"] == 119
    assert result["shocked_finish_day"] == 119
    assert result["shocked_slip_days"] == 0
    assert result["disrupted_activity_baseline_total_float_days"] == 15
    assert result["disrupted_activity_scenario_total_float_days"] == 1
    assert result["disrupted_activity_float_consumed_days"] == 14
    assert "consumed 14 of its 15 original float" in result["key_insight"]
    assert "only 1 day(s) of float remain" in result["key_insight"]


def test_exhausting_float_makes_a_second_path_critical_before_finish_moves():
    result = simulate_project("PR-01", 15, 4.5)
    assert result["baseline_finish_day"] == 119
    assert result["shocked_finish_day"] == 119
    assert result["shocked_slip_days"] == 0
    assert result["disrupted_activity_scenario_total_float_days"] == 0
    assert result["shocked_critical_path_count"] == 2
    assert "consumed all 15 day(s) of its original float" in result["key_insight"]
    assert "one additional day of delay would move modeled handover" in result["key_insight"]


def test_delay_one_day_past_available_float_moves_modeled_handover():
    result = simulate_project("PR-01", 16, 4.5)
    assert result["baseline_finish_day"] == 119
    assert result["shocked_finish_day"] == 120
    assert result["shocked_slip_days"] == 1
    assert result["disrupted_activity_baseline_total_float_days"] == 15
    assert result["disrupted_activity_scenario_total_float_days"] == 0
    assert "exceeds its original 15-day total float by 1 day(s)" in result["key_insight"]
    assert "handover moves by 1 day(s), to Day 120" in result["key_insight"]


def test_default_scenario_exposes_explicit_float_fields_without_changing_recommendation():
    result = simulate_project("ST-01", 14, 4.5)
    assert result["disrupted_activity_baseline_total_float_days"] == 0
    assert result["disrupted_activity_scenario_total_float_days"] == 0
    assert result["disrupted_activity_float_consumed_days"] == 0
    structure = next(item for item in result["activities"] if item["id"] == "ST-01")
    assert structure["total_float_change_days"] == 0
    assert result["recommended_action"]["id"] == "structural_recovery"


def test_dashboard_exposes_one_click_float_threshold_scenarios():
    response = client.get("/")
    assert response.status_code == 200
    page = response.text
    assert 'id="float14Case"' in page
    assert 'id="float15Case"' in page
    assert 'id="float16Case"' in page
    assert "Procurement +14d" in page
    assert "Procurement +15d" in page
    assert "Procurement +16d" in page
    assert "15 days of float" in page
    assert "moves modeled handover by 1 day" in page
