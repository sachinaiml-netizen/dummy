# Interview One-Page — Project Impact Lab

## 1. The problem, in plain language

**A construction activity can be late without making the whole project late. I want to show exactly when its remaining schedule buffer runs out, which work path then controls handover, and what recovery option is worth investigating.**

This is called **Float-Burn Watch**. It is a focused explanation workflow, not a claim that the scheduling method is new or that Prestige lacks this capability.

## 2. The 45-second explanation

“Construction work is connected: some activities must finish before others can start. A delay in one activity does not always move handover immediately, because the schedule may have spare time called total float. I built a small tool where a project-controls user can test a delay and see how that buffer shrinks, when a work path becomes critical, and whether the modeled handover date changes. It can also compare a few hypothetical recovery actions using visible cost assumptions. The sample data is invented. I want to find out whether this makes delay discussions clearer alongside the scheduling tools the team already uses.”

## 3. The simple example to demonstrate

The demo uses an invented schedule. Original handover is Day 119, and procurement has 15 days of total float.

| Button | What the model shows | What to say |
|---|---|---|
| Procurement +14 days | 1 day of float remains; handover stays Day 119 | “The buffer is nearly used, but the finish date has not moved.” |
| Procurement +15 days | 0 days of float; procurement/MEP becomes co-critical | “The buffer is exhausted. Two paths now control the finish.” |
| Procurement +16 days | Handover moves to Day 120 | “The delay has crossed the original buffer, so the modeled finish slips by one day.” |

These are deterministic calculations from synthetic durations and simple finish-to-start dependencies—not predictions about a Prestige project.

## 4. How the software works

```text
User clicks a scenario in the browser
              |
              v
Frontend JavaScript sends inputs to FastAPI
              |
              v
Python validates the request and runs CPM
              |
              v
API returns JSON: dates, float, paths, scenarios
              |
              v
JavaScript updates the dashboard
```

- **Frontend — `static/index.html`:** HTML defines the page, CSS styles it, and JavaScript handles buttons, sends requests and displays results.
- **Backend/API — `app/main.py`:** FastAPI exposes routes such as `GET /api/scenario` and `POST /api/scenario`.
- **Input checks — `app/schemas.py`:** Pydantic checks the request's fields and allowed ranges.
- **Scheduling maths — `app/decision_engine.py`:** validates the activity network, orders dependencies, calculates early/late dates and total float, and identifies critical paths.
- **Tests — `tests/test_scenario.py`:** verify expected results and edge cases. CI runs these tests automatically when code changes.

## 5. Optional configurable-schedule demo

If the interviewer asks whether this works only with the built-in example, click “Load sample” in the CSV intake panel, then “Validate & load”. The app validates the sample schedule, shows its baseline CPM result and lets you select an activity and inject a delay. You can upload your own small CSV in the same format.

Required columns: `task_id`, `task_name`, `duration_days`, `predecessors`. Separate multiple predecessor IDs with `|`. Optional columns are `owner` and `stream`. It rejects duplicate IDs, invalid durations, unknown predecessors and cycles. It does **not** parse native Primavera P6 XER/XML, connect to Prestige, or validate calendars/resources/contract rules. Do not upload confidential data.

## 6. Four terms to know

- **Activity:** a piece of work with an estimated duration.
- **Dependency:** a rule that one activity must happen before another.
- **Total float:** in this simplified model, the time an activity can move without moving the modeled project finish.
- **Critical path:** a connected path of activities that controls the earliest modeled finish. If two paths tie, both matter.

## 7. What the recovery-value number means

The demo uses:

`Illustrative net value = days recovered × assumed daily exposure − assumed action cost`

Example: `6 × ₹4.5 lakh − ₹8 lakh = ₹19 lakh`.

Both money inputs are placeholders. This is arithmetic for comparing scenarios, **not actual savings, a business case, or a recommendation to execute the action**. A project lead must validate safety, staffing, feasibility, contract conditions and cost data.

## 8. What is genuinely different—and what is not

CPM, total float, multiple critical paths, BIM, digital twins and AI-assisted construction risk analysis already exist in commercial products and large construction organisations. Do not claim this prototype is globally unique or better than Primavera, Autodesk Forma or Bentley.

The testable idea is narrower: **does one clear 14/15/16-day threshold walkthrough help a user explain float erosion and the handover consequence more quickly or consistently than their existing workflow?** If their current tools already do this equally well, this prototype has not shown additional value.

## 9. If asked, “Where is the AI?”

“The main scheduling calculation is deterministic CPM. I also built an experimental logistic-regression classifier trained on 70,000 synthetic examples and evaluated it on separate generated test data. That validates the model pipeline, not real construction prediction: the labels are simulated, and the score is not calibrated to Prestige outcomes. I used AI as a coding assistant, reviewed the logic and tests, and would only use real project predictions after approved historical snapshots, verified outcome labels and leakage-safe validation showed value beyond a transparent baseline.”

Do not claim that you personally typed every line if AI generated or revised code.

## 10. Separate experimental risk model

The dashboard also includes a separate logistic-regression classifier at /risk-model. It was trained on 70,000 synthetic samples, validated on 15,000, tested on 15,000 same-generator rows, and stress-checked on 15,000 shifted synthetic rows. Held-out ROC AUC is 0.800 and Brier score is 0.141, but these metrics only describe the simulator. Do not claim real-world accuracy or use the score to drive a project decision.

## 11. Three honest limitations

1. The task network and cost assumptions are synthetic.
2. The engine does not yet model work calendars, lags, resource constraints, site conditions or contract rules.
3. It is not connected to Prestige's systems or data and does not replace a scheduler.

## 12. Files to open if asked

1. `docs/PROBLEM_STATEMENT.md` — business problem and example.
2. `static/index.html` — visible interface and browser-to-API flow.
3. `app/main.py` — API routes.
4. `app/schemas.py` — request validation.
5. `app/decision_engine.py` — scheduling logic and CSV adapter.
6. `tests/test_scenario.py` and `tests/test_csv_schedule.py` — evidence the expected cases are tested.
7. `docs/architecture.md` — deeper technical details.
8. `docs/SYNTHETIC_RISK_MODEL.md` — training split, metrics and real-data validation gate.

**Interview rule:** explain the problem first, show the three thresholds second, explain the data flow third, and state the limitations before making any claim about business value.
