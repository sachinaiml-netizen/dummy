from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
SAMPLE = Path("static/sample_schedule.csv").read_text(encoding="utf-8")


def post_csv(csv_text, disrupted_task_id=None, delay_days=0):
    return client.post(
        "/api/schedule/analyze-csv",
        json={
            "csv_text": csv_text,
            "disrupted_task_id": disrupted_task_id,
            "delay_days": delay_days,
        },
    )


def test_sample_csv_route_downloads_a_real_csv_template():
    response = client.get("/sample-schedule.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "task_id,task_name,duration_days,predecessors" in response.text
    assert "PR-01,Long-lead procurement,26,DS-01" in response.text


def test_sample_schedule_csv_validates_and_returns_baseline_cpm():
    response = post_csv(SAMPLE)
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_type"] == "generic_csv_schedule"
    assert data["data_origin"] == "user_supplied_csv"
    assert "is_synthetic_demo" not in data
    assert data["activity_count"] == 8
    assert data["baseline_finish_day"] == 119
    assert data["scenario_finish_day"] == 119
    assert data["handover_slip_days"] == 0
    assert data["disrupted_task_id"] is None
    assert data["baseline_critical_path_count"] == 1
    assert any(task["task_id"] == "PR-01" and task["baseline_total_float_days"] == 15 for task in data["activities"])


def test_csv_threshold_cases_show_float_burn_and_finish_slip():
    one_day_left = post_csv(SAMPLE, "PR-01", 14)
    exhausted = post_csv(SAMPLE, "PR-01", 15)
    slipped = post_csv(SAMPLE, "PR-01", 16)

    assert one_day_left.status_code == 200
    assert one_day_left.json()["baseline_finish_day"] == 119
    assert one_day_left.json()["scenario_finish_day"] == 119
    assert one_day_left.json()["disrupted_task_baseline_total_float_days"] == 15
    assert one_day_left.json()["disrupted_task_scenario_total_float_days"] == 1
    assert one_day_left.json()["disrupted_task_float_consumed_days"] == 14

    assert exhausted.status_code == 200
    assert exhausted.json()["scenario_finish_day"] == 119
    assert exhausted.json()["disrupted_task_scenario_total_float_days"] == 0
    assert exhausted.json()["scenario_critical_path_count"] == 2

    assert slipped.status_code == 200
    assert slipped.json()["scenario_finish_day"] == 120
    assert slipped.json()["handover_slip_days"] == 1


def test_csv_adapter_is_independent_of_input_row_order():
    rows = SAMPLE.splitlines()
    reordered = "\n".join([rows[0]] + list(reversed(rows[1:]))) + "\n"
    response = post_csv(reordered)
    assert response.status_code == 200
    assert response.json()["baseline_finish_day"] == 119
    assert response.json()["activity_count"] == 8


def test_csv_rejects_missing_required_columns():
    response = post_csv("task_id,task_name\nA,Approval")
    assert response.status_code == 422
    assert "missing required columns" in response.json()["detail"]


def test_csv_rejects_duplicate_ids_with_row_number():
    csv_text = "task_id,task_name,duration_days,predecessors\nA,First,2,\nA,Second,3,\n"
    response = post_csv(csv_text)
    assert response.status_code == 422
    assert "Row 3: duplicate task_id 'A'" in response.json()["detail"]


def test_csv_rejects_unknown_predecessor_and_dependency_cycles():
    unknown = "task_id,task_name,duration_days,predecessors\nA,Task A,2,NOPE\n"
    cycle = "task_id,task_name,duration_days,predecessors\nA,Task A,2,B\nB,Task B,3,A\n"
    unknown_response = post_csv(unknown)
    assert unknown_response.status_code == 422
    assert "Unknown predecessor" in unknown_response.json()["detail"]
    cycle_response = post_csv(cycle)
    assert cycle_response.status_code == 422
    assert "Dependency cycle detected" in cycle_response.json()["detail"]


def test_csv_rejects_invalid_duration_and_missing_activity_name():
    bad_duration = "task_id,task_name,duration_days,predecessors\nA,Task A,-1,\n"
    missing_name = "task_id,task_name,duration_days,predecessors\nA,,2,\n"
    assert "positive finite number" in post_csv(bad_duration).json()["detail"]
    assert "task_name is required" in post_csv(missing_name).json()["detail"]


def test_csv_rejects_delay_without_activity_and_unknown_disrupted_activity():
    no_activity = post_csv(SAMPLE, None, 2)
    assert no_activity.status_code == 422
    assert "Select a disrupted task" in no_activity.json()["detail"]
    unknown = post_csv(SAMPLE, "NOT-IN-FILE", 1)
    assert unknown.status_code == 422
    assert "Unknown disrupted task ID" in unknown.json()["detail"]


def test_csv_rejects_beyond_the_supported_size_limit():
    response = post_csv("x" * 250001)
    assert response.status_code == 422


def test_dashboard_exposes_csv_workflow_and_accurate_format_caveat():
    response = client.get("/")
    assert response.status_code == 200
    page = response.text
    assert 'id="csvFile"' in page
    assert 'id="validateCsvButton"' in page
    assert 'id="runCsvScenarioButton"' in page
    assert 'id="csvSchedulePanel"' in page
    assert "does not parse native Primavera P6 XER/XML files" in page
    assert "No schedule is saved by this application" in page



def test_csv_accepts_utf8_bom_trimmed_headers_and_pipe_separated_predecessors():
    csv_text = (
        "\ufeff task_id , task_name , duration_days , predecessors , owner \n"
        "A,Approval,2,,PM\n"
        "B,Design,3,A| A2,Designer\n"
        "A2,Permit,1,,Reviewer\n"
    )
    response = post_csv(csv_text)
    assert response.status_code == 200
    data = response.json()
    assert data["activity_count"] == 3
    by_id = {row["task_id"]: row for row in data["activities"]}
    assert by_id["B"]["predecessors"] == ["A", "A2"]
    assert data["baseline_finish_day"] == 5


def test_csv_rejects_headers_that_collide_after_normalization():
    csv_text = (
        "task_id, task_id ,task_name,duration_days,predecessors\n"
        "A,A,Approval,2,\n"
    )
    response = post_csv(csv_text)
    assert response.status_code == 422
    assert "duplicate column names" in response.json()["detail"]


def test_csv_rejects_rows_with_more_values_than_declared_columns():
    csv_text = (
        "task_id,task_name,duration_days,predecessors\n"
        "A,Approval,2,,unexpected\n"
    )
    response = post_csv(csv_text)
    assert response.status_code == 422
    assert "more values than the header" in response.json()["detail"]


def test_csv_rejects_more_than_supported_activity_count():
    rows = ["task_id,task_name,duration_days,predecessors"]
    rows.extend(f"T{i},Task {i},1," for i in range(2001))
    response = post_csv("\\n".join(rows))
    assert response.status_code == 422
    assert "2,000-activity limit" in response.json()["detail"]
