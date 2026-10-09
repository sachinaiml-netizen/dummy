# Project Impact Lab
## Critical-path-aware construction decision rehearsal

**Research proof of concept · synthetic schedule and cost assumptions · no Prestige confidential data · not a production forecasting system**

Project Impact Lab explores a focused question: **when a construction activity slips, which response is actually worth paying for, given the project's dependency network and the effect on the completion date?**

A conventional risk score is not enough for that decision. This prototype injects a delay into a task, propagates it through dependent activities, tests a small set of illustrative recovery actions, and ranks the actions by estimated net value. It is designed as a possible decision-support layer alongside existing BIM and scheduling tools—not as a replacement for Autodesk, Primavera, or a project manager.

## Why this is a more useful interview demonstration

It contains two deliberately contrasting scenarios:

1. **Critical-path case:** adding 14 days to the synthetic structure activity moves handover from Day 119 to Day 133. A focused structural recovery crew recovers 6 days. At the editable illustrative assumption of ₹4.5 lakh per delay day and an assumed ₹8 lakh action cost, the calculated net value is ₹19 lakh.
2. **Schedule-float case:** adding 14 days to long-lead procurement does not move modeled handover beyond Day 119, because the facade/finishes chain still controls the finish. The model does not recommend paying ₹12 lakh to expedite procurement for finish-date recovery in that scenario.

These are deterministic examples built from made-up durations, dependencies, action effects and costs. **They are not claimed savings, probabilities, calibrated results, or estimates of Prestige's real project economics.** Their value is that the decision logic can be inspected, challenged and tested.

## What is implemented

- Interactive browser dashboard served by FastAPI.
- Editable disruption activity, delay length and daily-exposure assumption.
- Dependency graph with forward-pass schedule calculation.
- Baseline versus disruption comparison, downstream impact trace and critical-chain display.
- Comparison of five hypothetical intervention options plus no action.
- Ranking by days recovered, action cost and modelled net value.
- A 3×3 deterministic assumption stress grid showing whether the preferred action remains stable when delay and daily-exposure assumptions change.
- Pydantic input validation and tests for critical-path impact, schedule float, ranking and invalid inputs.
- Existing /risk endpoint retained for the original snapshot risk-score prototype.

## Architecture

    User scenario
       |
       v
    Pydantic validation
       |
       v
    Synthetic activity dependency graph
       |
       +--> Baseline forward pass --> baseline finish and critical chain
       |
       +--> Inject one task delay --> impacted finish and affected successors
       |
       +--> Evaluate each recovery action --> new schedule and finish date
       |
       v
    Rank: recovered days x assumed daily exposure - assumed action cost
       |
       v
    Explainable decision brief + activity-level impact trace

## Run locally

Python 3.12 is used in the GitHub Actions workflow.

### Windows PowerShell

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    uvicorn app.main:app --reload

### macOS / Linux

    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Open http://127.0.0.1:8000 for the dashboard and http://127.0.0.1:8000/docs for the API documentation.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Health check |
| GET | /api/catalog | Synthetic task and intervention catalog |
| GET | /api/scenario | Default structural-delay scenario |
| POST | /api/scenario | Recompute impact for a supplied scenario |
| POST | /risk | Legacy telemetry-based risk-score prototype |

Example request to POST /api/scenario:

    {
      "disrupted_activity_id": "ST-01",
      "delay_days": 14,
      "exposure_lakh_per_day": 4.5
    }

## Tests

    pytest -q

## Model card and limits

- The decision engine is a **deterministic critical-path simulation**, not a trained delay-prediction model and not a causal model.
- The synthetic network has eight activities and simplified finish-to-start dependencies. It does not model working calendars, lag types, resource levelling, weather calendars, cash-flow, contract terms, uncertainty distributions or change orders.
- Intervention durations and costs are fixed illustrative assumptions. A real use case would require feasible alternatives approved by delivery teams and current cost inputs.
- The recommendation stability panel varies the injected delay by ±4 days and the daily-exposure assumption by ±25% in a small deterministic grid. It is a sensitivity check, not a probability estimate, confidence interval, Monte Carlo run or proof of robustness beyond the tested range.
- The existing /risk endpoint retains a separate Isolation Forest that is fitted to a generated synthetic reference distribution. That anomaly score is **not** a calibrated probability and should not be represented as validated against real project outcomes.
- No Prestige internal data or live Autodesk / Primavera / ERP / RERA connection is used. All project tasks and values are generic synthetic examples.
- A credible pilot would need permissioned schedule histories, stable task IDs, source timestamps, project calendars, actual planned/actual outcomes, back-testing, drift/error monitoring, access controls and human sign-off.

## Positioning for a real-estate technology discussion

Prestige publicly announced a three-year digital-transformation collaboration with Autodesk in April 2026. Autodesk also documents existing construction-risk features, while Oracle Primavera Cloud supports risk analysis connected to scheduling. The defensible proposal is therefore **not another dashboard**: it is to test whether a small, explainable decision-rehearsal layer could help delivery teams compare schedule recovery actions across approved data sources.

Any relevance to Prestige's actual processes remains a hypothesis to validate with its engineering-transformation and project-controls teams.

## Public research references

- Autodesk Research, Intelligent Construction: https://www.research.autodesk.com/projects/intelligent-construction/
- Autodesk Construction IQ documentation: https://help.autodesk.com/cloudhelp/ENU/Docs-Insight/files/Insight_Construction_IQ.html
- Oracle Primavera Cloud overview: https://www.oracle.com/in/construction-engineering/primavera-cloud-project-management/
- Prestige Group press-release index: https://www.prestigeconstructions.com/kn/news/2026/april

Prepared as a student proof of concept for a technology discussion. No affiliation with, endorsement by, or internal access to Prestige Group is implied.
