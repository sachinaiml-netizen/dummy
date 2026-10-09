from __future__ import annotations

from copy import deepcopy
from typing import Any

# Synthetic demonstration network. Durations and money values are illustrative,
# not Prestige project data or calibrated construction benchmarks.
TASKS: list[dict[str, Any]] = [
    {"id": "AP-01", "name": "Approval package", "duration": 18, "predecessors": [], "stream": "Approvals", "owner": "Project controls"},
    {"id": "DS-01", "name": "Design freeze", "duration": 12, "predecessors": ["AP-01"], "stream": "Design", "owner": "Design coordination"},
    {"id": "ST-01", "name": "Structure works", "duration": 35, "predecessors": ["DS-01"], "stream": "Construction", "owner": "Civil contractor"},
    {"id": "PR-01", "name": "Long-lead procurement", "duration": 26, "predecessors": ["DS-01"], "stream": "Supply chain", "owner": "Procurement"},
    {"id": "ME-01", "name": "MEP rough-in", "duration": 18, "predecessors": ["ST-01", "PR-01"], "stream": "MEP", "owner": "MEP contractor"},
    {"id": "FC-01", "name": "Facade closure", "duration": 24, "predecessors": ["ST-01"], "stream": "Envelope", "owner": "Facade contractor"},
    {"id": "IN-01", "name": "Interior finishes", "duration": 20, "predecessors": ["ME-01", "FC-01"], "stream": "Finishes", "owner": "Finishes contractor"},
    {"id": "HO-01", "name": "Commissioning & handover", "duration": 10, "predecessors": ["IN-01"], "stream": "Handover", "owner": "Project delivery"},
]

INTERVENTIONS: list[dict[str, Any]] = [
    {"id": "none", "title": "No paid intervention", "target": None, "recovery_days": 0, "cost_lakh": 0.0,
     "rationale": "Preserve budget when a change does not improve the projected project finish."},
    {"id": "structural_recovery", "title": "Focused structural recovery crew", "target": "ST-01", "recovery_days": 6, "cost_lakh": 8.0,
     "rationale": "Add a focused crew and resequence approved structural work; requires a safe, feasible recovery plan."},
    {"id": "supplier_expedite", "title": "Expedite long-lead materials", "target": "PR-01", "recovery_days": 8, "cost_lakh": 12.0,
     "rationale": "Use an approved supplier expediting option; commercial and quality checks remain mandatory."},
    {"id": "mep_second_shift", "title": "Temporary MEP second shift", "target": "ME-01", "recovery_days": 4, "cost_lakh": 7.0,
     "rationale": "Add a temporary shift where access, labour availability and safety permit."},
    {"id": "facade_prefab", "title": "Prefabricated facade package", "target": "FC-01", "recovery_days": 5, "cost_lakh": 18.0,
     "rationale": "Evaluate off-site preparation to compress facade installation, subject to design and procurement readiness."},
    {"id": "handover_sprint", "title": "Handover-readiness sprint", "target": "HO-01", "recovery_days": 3, "cost_lakh": 3.0,
     "rationale": "Close documentation, testing and commissioning prerequisites in parallel where permitted."},
]
EXAMPLE_EXPOSURE_LAKH_PER_DAY = 4.5
FINAL_TASK_ID = "HO-01"


def analyze_schedule(
    tasks: list[dict[str, Any]],
    duration_overrides: dict[str, int | float] | None = None,
    *,
    max_paths_to_return: int = 256,
) -> dict[str, Any]:
    """Run CPM forward/backward passes on a finish-to-start dependency network.

    Tasks may be supplied in any order. This analyzer validates identifiers,
    durations and links, topologically sorts the graph, calculates early/late
    dates and total float, and preserves tied critical paths. It does not model
    working calendars, lags, constraints or resource levelling.
    """
    import heapq
    import math

    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks must be a non-empty list")
    if isinstance(max_paths_to_return, bool) or not isinstance(max_paths_to_return, int) or max_paths_to_return < 1:
        raise ValueError("max_paths_to_return must be a positive integer")

    original_index: dict[str, int] = {}
    by_id: dict[str, dict[str, Any]] = {}
    predecessors: dict[str, list[str]] = {}
    durations: dict[str, int | float] = {}

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise ValueError(f"Task at index {index} must be an object")
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id.strip() or task_id != task_id.strip():
            raise ValueError(f"Task at index {index} must have a non-empty id without surrounding whitespace")
        if task_id in by_id:
            raise ValueError(f"Duplicate task id: {task_id}")
        duration = task.get("duration")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ValueError(f"Duration for {task_id} must be a positive finite number")
        if not math.isfinite(float(duration)) or duration <= 0:
            raise ValueError(f"Duration for {task_id} must be a positive finite number")
        pred_list = task.get("predecessors", [])
        if not isinstance(pred_list, list):
            raise ValueError(f"Predecessors for {task_id} must be a list")
        if any(not isinstance(pred, str) or not pred.strip() or pred != pred.strip() for pred in pred_list):
            raise ValueError(f"Predecessors for {task_id} must be trimmed, non-empty string ids")
        if len(set(pred_list)) != len(pred_list):
            raise ValueError(f"Duplicate predecessor in task {task_id}")
        if task_id in pred_list:
            raise ValueError(f"Task {task_id} cannot depend on itself")
        by_id[task_id] = task
        original_index[task_id] = index
        predecessors[task_id] = list(pred_list)
        durations[task_id] = duration

    for task_id, pred_list in predecessors.items():
        for pred in pred_list:
            if pred not in by_id:
                raise ValueError(f"Unknown predecessor {pred!r} referenced by task {task_id}")

    if duration_overrides is not None and not isinstance(duration_overrides, dict):
        raise ValueError("duration_overrides must be a dictionary")
    for task_id, duration in (duration_overrides or {}).items():
        if task_id not in by_id:
            raise ValueError(f"Duration override references unknown task: {task_id}")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            raise ValueError(f"Duration override for {task_id} must be a positive finite number")
        if not math.isfinite(float(duration)) or duration <= 0:
            raise ValueError(f"Duration override for {task_id} must be a positive finite number")
        durations[task_id] = duration

    successors: dict[str, list[str]] = {task_id: [] for task_id in by_id}
    indegree: dict[str, int] = {}
    for task_id, pred_list in predecessors.items():
        indegree[task_id] = len(pred_list)
        for pred in pred_list:
            successors[pred].append(task_id)
    for successor_list in successors.values():
        successor_list.sort(key=lambda task_id: original_index[task_id])

    ready: list[tuple[int, str]] = [
        (original_index[task_id], task_id)
        for task_id, degree in indegree.items()
        if degree == 0
    ]
    heapq.heapify(ready)
    topo_order: list[str] = []
    while ready:
        _, task_id = heapq.heappop(ready)
        topo_order.append(task_id)
        for successor in successors[task_id]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                heapq.heappush(ready, (original_index[successor], successor))
    if len(topo_order) != len(by_id):
        cyclic = [task_id for task_id, degree in indegree.items() if degree > 0]
        raise ValueError(f"Dependency cycle detected involving: {', '.join(cyclic)}")

    early_start: dict[str, int | float] = {}
    early_finish: dict[str, int | float] = {}
    for task_id in topo_order:
        early_start[task_id] = max(
            (early_finish[pred] for pred in predecessors[task_id]),
            default=0,
        )
        early_finish[task_id] = early_start[task_id] + durations[task_id]

    terminal_ids = [task_id for task_id in topo_order if not successors[task_id]]
    project_finish = max(early_finish[task_id] for task_id in terminal_ids)

    late_start: dict[str, int | float] = {}
    late_finish: dict[str, int | float] = {}
    for task_id in reversed(topo_order):
        if successors[task_id]:
            late_finish[task_id] = min(late_start[succ] for succ in successors[task_id])
        else:
            late_finish[task_id] = project_finish
        late_start[task_id] = late_finish[task_id] - durations[task_id]

    epsilon = 1e-9
    total_float: dict[str, int | float] = {}
    critical_ids: list[str] = []
    for task_id in topo_order:
        raw_float = late_start[task_id] - early_start[task_id]
        value: int | float = 0 if abs(raw_float) < epsilon else raw_float
        total_float[task_id] = value
        if value == 0:
            critical_ids.append(task_id)

    critical_set = set(critical_ids)
    critical_successors: dict[str, list[str]] = {task_id: [] for task_id in by_id}
    critical_predecessors: dict[str, list[str]] = {task_id: [] for task_id in by_id}
    for task_id in topo_order:
        if task_id not in critical_set:
            continue
        for succ in successors[task_id]:
            if (
                succ in critical_set
                and abs(float(early_finish[task_id]) - float(early_start[succ])) < epsilon
            ):
                critical_successors[task_id].append(succ)
                critical_predecessors[succ].append(task_id)

    critical_sources = [
        task_id for task_id in topo_order
        if task_id in critical_set and not critical_predecessors[task_id]
    ]
    critical_terminals = {
        task_id for task_id in terminal_ids
        if task_id in critical_set
        and abs(float(early_finish[task_id]) - float(project_finish)) < epsilon
    }

    # Count paths exactly with dynamic programming, but only materialize a bounded
    # number for responses so tied networks cannot cause unbounded response growth.
    path_counts: dict[str, int] = {task_id: 0 for task_id in by_id}
    for task_id in critical_sources:
        path_counts[task_id] = 1
    for task_id in topo_order:
        for succ in critical_successors[task_id]:
            path_counts[succ] += path_counts[task_id]
    critical_path_count = sum(path_counts[task_id] for task_id in critical_terminals)

    critical_paths: list[list[str]] = []
    truncated = False
    # Iterative DFS avoids Python recursion limits on long but valid activity chains.
    stop_enumerating = False
    for source in critical_sources:
        if stop_enumerating:
            break
        stack: list[tuple[str, list[str]]] = [(source, [source])]
        while stack:
            task_id, path = stack.pop()
            if task_id in critical_terminals:
                critical_paths.append(path)
                if len(critical_paths) >= max_paths_to_return:
                    truncated = critical_path_count > len(critical_paths)
                    stop_enumerating = True
                    break
                continue
            for succ in reversed(critical_successors[task_id]):
                stack.append((succ, path + [succ]))

    return {
        "start": early_start,
        "finish": early_finish,
        "duration": durations,
        "early_start": early_start,
        "early_finish": early_finish,
        "late_start": late_start,
        "late_finish": late_finish,
        "total_float": total_float,
        "critical_task_ids": critical_ids,
        "critical_paths": critical_paths,
        "critical_path_count": critical_path_count,
        "critical_paths_truncated": truncated,
        "terminal_task_ids": terminal_ids,
        "project_finish": project_finish,
        "topological_order": topo_order,
    }


def _schedule(
    extra_delay_activity_id: str | None = None,
    delay_days: int = 0,
    intervention: dict[str, Any] | None = None,
) -> dict[str, Any]:
    duration = {task["id"]: task["duration"] for task in TASKS}

    if extra_delay_activity_id is not None:
        if extra_delay_activity_id not in duration:
            raise ValueError(f"Unknown activity: {extra_delay_activity_id}")
        if isinstance(delay_days, bool) or not isinstance(delay_days, int) or not 0 <= delay_days <= 60:
            raise ValueError("delay_days must be an integer between 0 and 60")
        duration[extra_delay_activity_id] += delay_days

    if intervention and intervention["target"] and intervention["recovery_days"]:
        target = intervention["target"]
        if target not in duration:
            raise ValueError(f"Unknown intervention target: {target}")
        # Recovery cannot make an activity have a zero/negative duration.
        duration[target] = max(1, duration[target] - intervention["recovery_days"])

    schedule = analyze_schedule(TASKS, duration)
    return schedule


def _critical_chain(schedule: dict[str, Any]) -> list[str]:
    """Return one deterministic representative path for legacy UI compatibility."""
    paths = schedule.get("critical_paths", [])
    return list(paths[0]) if paths else []

def _descendants(activity_id: str) -> list[str]:
    descendants: set[str] = set()
    changed = True
    while changed:
        changed = False
        for task in TASKS:
            if task["id"] not in descendants and (
                activity_id in task["predecessors"]
                or any(pred in descendants for pred in task["predecessors"])
            ):
                descendants.add(task["id"])
                changed = True
    return [task["id"] for task in TASKS if task["id"] in descendants]



def _selected_action_id(
    disrupted_activity_id: str,
    delay_days: int,
    exposure_lakh_per_day: float,
) -> str:
    baseline_finish = _schedule()["finish"][FINAL_TASK_ID]
    shocked_finish = _schedule(disrupted_activity_id, delay_days)["finish"][FINAL_TASK_ID]
    slip_days = max(0, shocked_finish - baseline_finish)
    rows: list[dict[str, Any]] = []
    for action in INTERVENTIONS:
        scenario = _schedule(
            disrupted_activity_id,
            delay_days,
            action if action["id"] != "none" else None,
        )
        finish_day = scenario["finish"][FINAL_TASK_ID]
        days_recovered = min(max(0, shocked_finish - finish_day), slip_days)
        net_value = days_recovered * exposure_lakh_per_day - action["cost_lakh"]
        rows.append({
            "id": action["id"],
            "days_recovered": days_recovered,
            "net_value_lakh": round(net_value, 2),
            "cost_lakh": action["cost_lakh"],
        })
    rows.sort(
        key=lambda row: (row["net_value_lakh"], row["days_recovered"], -row["cost_lakh"]),
        reverse=True,
    )
    best = rows[0]
    if best["id"] == "none" or best["net_value_lakh"] <= 0:
        return "none"
    return best["id"]


def _sensitivity_summary(
    disrupted_activity_id: str,
    delay_days: int,
    exposure_lakh_per_day: float,
) -> dict[str, Any]:
    # A deterministic 3x3 stress grid, not a probability distribution or Monte Carlo model.
    delays = sorted({max(0, delay_days - 4), delay_days, min(60, delay_days + 4)})
    exposures = sorted({
        round(max(0.0, exposure_lakh_per_day * 0.75), 2),
        round(exposure_lakh_per_day, 2),
        round(min(100.0, exposure_lakh_per_day * 1.25), 2),
    })
    counts = {action["id"]: 0 for action in INTERVENTIONS}
    trials = 0
    for test_delay in delays:
        for test_exposure in exposures:
            selected = _selected_action_id(
                disrupted_activity_id,
                test_delay,
                test_exposure,
            )
            counts[selected] += 1
            trials += 1

    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    dominant_id, dominant_count = ranked[0]
    titles = {action["id"]: action["title"] for action in INTERVENTIONS}
    return {
        "method": "3x3 deterministic stress grid",
        "tested_scenarios": trials,
        "delay_range_days": [min(delays), max(delays)],
        "exposure_range_lakh_per_day": [min(exposures), max(exposures)],
        "action_frequency": [
            {
                "id": action_id,
                "title": titles[action_id],
                "selected_trials": counts[action_id],
                "share_pct": round(100 * counts[action_id] / trials, 1),
            }
            for action_id, _ in ranked
            if counts[action_id] > 0
        ],
        "most_common_action_id": dominant_id,
        "most_common_action_title": titles[dominant_id],
        "stability_pct": round(100 * dominant_count / trials, 1),
        "stable": dominant_count == trials,
        "interpretation": (
            "Same response in every tested scenario; stable only within this small stress grid."
            if dominant_count == trials
            else "Response changes under tested assumptions; treat the ranking as fragile and request human review."
        ),
    }


def simulate_project(
    disrupted_activity_id: str = "ST-01",
    delay_days: int = 14,
    exposure_lakh_per_day: float = EXAMPLE_EXPOSURE_LAKH_PER_DAY,
) -> dict[str, Any]:
    known_ids = {task["id"] for task in TASKS}
    if disrupted_activity_id not in known_ids:
        raise ValueError(f"Unknown activity: {disrupted_activity_id}")
    if not 0 <= delay_days <= 60:
        raise ValueError("delay_days must be between 0 and 60")
    if not 0 <= exposure_lakh_per_day <= 100:
        raise ValueError("exposure_lakh_per_day must be between 0 and 100")

    baseline = _schedule()
    shocked = _schedule(disrupted_activity_id, delay_days)
    baseline_finish = baseline["finish"][FINAL_TASK_ID]
    shocked_finish = shocked["finish"][FINAL_TASK_ID]
    slip_days = max(0, shocked_finish - baseline_finish)
    gross_exposure = slip_days * exposure_lakh_per_day

    intervention_rows: list[dict[str, Any]] = []
    schedules_by_intervention: dict[str, dict[str, Any]] = {}
    for action in INTERVENTIONS:
        scenario = _schedule(disrupted_activity_id, delay_days, action if action["id"] != "none" else None)
        schedules_by_intervention[action["id"]] = scenario
        finish_day = scenario["finish"][FINAL_TASK_ID]
        # Only credit an intervention for recovering the delay introduced by this scenario,
        # not for making the original baseline unrealistically faster.
        saved_days = min(max(0, shocked_finish - finish_day), slip_days)
        avoided_exposure = saved_days * exposure_lakh_per_day
        net_value = avoided_exposure - action["cost_lakh"]
        intervention_rows.append({
            "id": action["id"],
            "title": action["title"],
            "target": action["target"],
            "recovery_days_assumed": action["recovery_days"],
            "cost_lakh": round(action["cost_lakh"], 2),
            "project_finish_day": finish_day,
            "slip_days_after_action": max(0, finish_day - baseline_finish),
            "days_recovered": saved_days,
            "delay_exposure_avoided_lakh": round(avoided_exposure, 2),
            "net_value_lakh": round(net_value, 2),
            "rationale": action["rationale"],
        })

    intervention_rows.sort(key=lambda row: (row["net_value_lakh"], row["days_recovered"], -row["cost_lakh"]), reverse=True)
    best_row = intervention_rows[0]
    if best_row["id"] == "none" or best_row["net_value_lakh"] <= 0:
        best_row = next(row for row in intervention_rows if row["id"] == "none")
    recommended_action_id = best_row["id"]
    best_schedule = schedules_by_intervention[recommended_action_id]

    task_by_id = {task["id"]: task for task in TASKS}
    affected_descendants = _descendants(disrupted_activity_id)
    activities: list[dict[str, Any]] = []
    for task in TASKS:
        task_id = task["id"]
        activities.append({
            **task,
            "baseline_start_day": baseline["start"][task_id],
            "baseline_finish_day": baseline["finish"][task_id],
            "shocked_start_day": shocked["start"][task_id],
            "shocked_finish_day": shocked["finish"][task_id],
            "finish_shift_days": shocked["finish"][task_id] - baseline["finish"][task_id],
            "recommended_start_day": best_schedule["start"][task_id],
            "recommended_finish_day": best_schedule["finish"][task_id],
            "baseline_total_float_days": baseline["total_float"][task_id],
            "shocked_total_float_days": shocked["total_float"][task_id],
            "total_float_change_days": shocked["total_float"][task_id] - baseline["total_float"][task_id],
            "recommended_total_float_days": best_schedule["total_float"][task_id],
            "on_baseline_critical_path": task_id in baseline["critical_task_ids"],
            "on_shocked_critical_path": task_id in shocked["critical_task_ids"],
            # Legacy field names retained for clients using the original response shape.
            "on_baseline_critical_chain": task_id in baseline["critical_task_ids"],
            "on_shocked_critical_chain": task_id in shocked["critical_task_ids"],
            "downstream_of_disruption": task_id in affected_descendants,
        })

    disrupted = task_by_id[disrupted_activity_id]
    disrupted_baseline_float = baseline["total_float"][disrupted_activity_id]
    disrupted_scenario_float = shocked["total_float"][disrupted_activity_id]
    float_consumed_days = max(0, disrupted_baseline_float - disrupted_scenario_float)

    # Prefer the most decision-relevant explanation: float being consumed,
    # float reaching zero, or the delay crossing the activity's available float.
    if delay_days > 0 and disrupted_baseline_float > 0 and slip_days > 0:
        key_insight = (
            f"The {delay_days}-day delay on {disrupted['name']} exceeds its original "
            f"{disrupted_baseline_float}-day total float by {max(0, delay_days - disrupted_baseline_float)} day(s). "
            f"Under this simplified network, modeled handover moves by {slip_days} day(s), to Day {shocked_finish}."
        )
    elif delay_days > 0 and disrupted_baseline_float > 0 and disrupted_scenario_float == 0:
        key_insight = (
            f"The {delay_days}-day delay on {disrupted['name']} has consumed all "
            f"{disrupted_baseline_float} day(s) of its original float. Handover has not moved yet, "
            "but this path is now critical alongside the other controlling path; one additional day of delay "
            "would move modeled handover under these assumptions."
        )
    elif (
        delay_days > 0
        and disrupted_baseline_float > 0
        and disrupted_scenario_float <= 3
        and disrupted_scenario_float > 0
    ):
        key_insight = (
            f"The {delay_days}-day delay on {disrupted['name']} has consumed "
            f"{float_consumed_days} of its {disrupted_baseline_float} original float day(s). "
            f"Handover has not moved yet, but only {disrupted_scenario_float} day(s) of float remain."
        )
    elif slip_days == 0 and delay_days > 0:
        key_insight = (
            f"The {delay_days}-day delay on {disrupted['name']} does not change the modeled handover date. "
            "The remaining dependency path still controls completion, so a paid recovery action is not justified "
            "by finish-date savings under these assumptions."
        )
    elif recommended_action_id != "none":
        key_insight = (
            f"{best_row['title']} is the highest-value modeled response: it recovers {best_row['days_recovered']} "
            f"day(s), for an illustrative net value of ₹{best_row['net_value_lakh']:.1f} lakh at "
            f"₹{exposure_lakh_per_day:.1f} lakh per day. Validate feasibility, scope and costs with the project team."
        )
    else:
        key_insight = (
            "No paid intervention has positive modeled net value under the current assumptions. "
            "Review the exposure rate and intervention costs before spending."
        )

    return {
        "product_name": "Project Impact Lab",
        "engine": "Deterministic dependency-network / critical-path simulation",
        "is_synthetic_demo": True,
        "disrupted_activity_id": disrupted_activity_id,
        "disrupted_activity_name": disrupted["name"],
        "disrupted_activity_baseline_total_float_days": disrupted_baseline_float,
        "disrupted_activity_scenario_total_float_days": disrupted_scenario_float,
        "disrupted_activity_float_consumed_days": float_consumed_days,
        "delay_days": delay_days,
        "exposure_lakh_per_day": round(exposure_lakh_per_day, 2),
        "baseline_finish_day": baseline_finish,
        "shocked_finish_day": shocked_finish,
        "shocked_slip_days": slip_days,
        "gross_delay_exposure_lakh": round(gross_exposure, 2),
        "recommended_finish_day": best_schedule["finish"][FINAL_TASK_ID],
        "recommended_slip_days": max(0, best_schedule["finish"][FINAL_TASK_ID] - baseline_finish),
        "recommended_action": best_row,
        "ranked_interventions": intervention_rows,
        "baseline_critical_chain": _critical_chain(baseline),
        "shocked_critical_chain": _critical_chain(shocked),
        "recommended_critical_chain": _critical_chain(best_schedule),
        "baseline_critical_paths": baseline["critical_paths"],
        "shocked_critical_paths": shocked["critical_paths"],
        "recommended_critical_paths": best_schedule["critical_paths"],
        "baseline_critical_path_count": baseline["critical_path_count"],
        "shocked_critical_path_count": shocked["critical_path_count"],
        "recommended_critical_path_count": best_schedule["critical_path_count"],
        "critical_paths_truncated": any((baseline["critical_paths_truncated"], shocked["critical_paths_truncated"], best_schedule["critical_paths_truncated"])),
        "impacted_activity_ids": [disrupted_activity_id] + affected_descendants,
        "activities": activities,
        "key_insight": key_insight,
        "sensitivity": _sensitivity_summary(disrupted_activity_id, delay_days, exposure_lakh_per_day),
        "assumptions": [
            "All task names, durations, dependencies, recovery estimates and cost values are synthetic demo inputs.",
            "The schedule engine is deterministic and uses longest-path dependency propagation; it is not a trained delay-prediction model.",
            "Illustrative delay exposure is editable and is not Prestige's actual daily project cost.",
            "No Autodesk, Primavera, ERP, RERA or internal Prestige system is connected.",
            "A production pilot requires approved project data, schedule-calendar rules, uncertainty distributions, expert review and back-testing.",
        ],
    }


def get_catalog() -> dict[str, Any]:
    return {
        "activities": deepcopy(TASKS),
        "interventions": deepcopy(INTERVENTIONS),
        "default_exposure_lakh_per_day": EXAMPLE_EXPOSURE_LAKH_PER_DAY,
    }
