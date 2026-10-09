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


def _schedule(
    extra_delay_activity_id: str | None = None,
    delay_days: int = 0,
    intervention: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tasks = deepcopy(TASKS)
    duration = {task["id"]: task["duration"] for task in tasks}

    if extra_delay_activity_id and delay_days:
        duration[extra_delay_activity_id] += delay_days

    if intervention and intervention["target"] and intervention["recovery_days"]:
        target = intervention["target"]
        # Recovery cannot make an activity have a zero/negative duration.
        duration[target] = max(1, duration[target] - intervention["recovery_days"])

    start: dict[str, int] = {}
    finish: dict[str, int] = {}
    for task in tasks:  # TASKS is stored in topological order.
        predecessors = task["predecessors"]
        start[task["id"]] = max((finish[pred] for pred in predecessors), default=0)
        finish[task["id"]] = start[task["id"]] + duration[task["id"]]

    return {"start": start, "finish": finish, "duration": duration}


def _critical_chain(schedule: dict[str, Any]) -> list[str]:
    by_id = {task["id"]: task for task in TASKS}
    current = FINAL_TASK_ID
    reverse_chain = [current]
    while by_id[current]["predecessors"]:
        preds = by_id[current]["predecessors"]
        # A predecessor on the controlling path finishes exactly at current's start.
        controlling = max(preds, key=lambda pred: (schedule["finish"][pred], -next(
            i for i, task in enumerate(TASKS) if task["id"] == pred
        )))
        if schedule["finish"][controlling] < schedule["start"][current]:
            break
        reverse_chain.append(controlling)
        current = controlling
    return list(reversed(reverse_chain))


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
            "on_baseline_critical_chain": task_id in _critical_chain(baseline),
            "on_shocked_critical_chain": task_id in _critical_chain(shocked),
            "downstream_of_disruption": task_id in affected_descendants,
        })

    disrupted = task_by_id[disrupted_activity_id]
    if slip_days == 0 and delay_days > 0:
        key_insight = (
            f"The {delay_days}-day delay on {disrupted['name']} does not change the modeled handover date. "
            "A parallel dependency chain still controls completion, so a paid recovery action is not justified "
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
        "impacted_activity_ids": [disrupted_activity_id] + affected_descendants,
        "activities": activities,
        "key_insight": key_insight,
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
