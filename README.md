# Project Impact Lab
## Critical-path-aware construction decision rehearsal

**Research proof of concept · synthetic schedule and cost assumptions · no Prestige confidential data · not a production forecasting system**

**Problem being tested:** when a delay is reported, is it consuming schedule float or moving handover—and what recovery option should a project-controls lead investigate first? Start with the [Interview One-Page](docs/INTERVIEW_ONE_PAGE.md), then use the [Problem Statement](docs/PROBLEM_STATEMENT.md), [Competitive Research](docs/COMPETITIVE_RESEARCH.md) and [Six-Hour Learning Guide](docs/SIX_HOUR_LEARNING_GUIDE.md).

Project Impact Lab explores a focused question: **when a construction activity slips, which response is actually worth paying for, given the project's dependency network and the effect on the completion date?**

The current feature is called **Float-Burn Watch**: it demonstrates how an activity's available schedule buffer shrinks as a delay is injected. This is a focused scenario explanation, not an assertion of a unique market capability. A conventional risk score is not enough for that decision. This prototype injects a delay into a task, propagates it through dependent activities, tests a small set of illustrative recovery actions, and ranks the actions by estimated net value. It is designed as a possible decision-support layer alongside existing BIM and scheduling tools—not as a replacement for Autodesk, Primavera, or a project manager.


## Public preview

- **Live browser preview:** https://project-impact-lab.vercel.app/
- **Health API:** https://project-impact-lab.vercel.app/health
- **Default scenario API:** https://project-impact-lab.vercel.app/api/scenario
- **Synthetic task catalog:** https://project-impact-lab.vercel.app/api/catalog
- **CSV sample template:** https://project-impact-lab.vercel.app/sample-schedule.csv
- **CSV analysis endpoint:** `POST https://project-impact-lab.vercel.app/api/schedule/analyze-csv`

The public URL and the three GET routes were checked after deployment on 2026-10-09. The default scenario response returns baseline handover Day 119, no-action handover Day 133, and the explicitly illustrative structural recovery option. Automated CI separately tests the POST scenario route and its validation.

**Deployment limitation:** the Vercel deployment is currently a manual source upload. The connected Vercel account did not have a GitHub Login Connection, so Vercel is not linked to this repository and future pushes to main will not automatically deploy. Re-deploy the latest main source or establish the GitHub connection in Vercel before relying on automatic releases. No database, custom domain, secret, or paid add-on was configured; the connected account's full billing/plan status was not readable through the available connection.

## CSV schedule intake

The app accepts a small, documented CSV adapter format so a user can inspect a task network other than the built-in example. Download [the synthetic sample CSV](https://project-impact-lab.vercel.app/sample-schedule.csv) and upload it in the dashboard, or submit the same text to `POST /api/schedule/analyze-csv` as JSON:

```json
{
  "csv_text": "task_id,task_name,duration_days,predecessors\\nA,Approval,4,\\nB,Structure,8,A\\nC,Handover,2,B\\n",
  "disrupted_task_id": "B",
  "delay_days": 3
}
```

Required columns: `task_id`, `task_name`, `duration_days`, and `predecessors`. Optional columns: `owner` and `stream`. Multiple predecessor IDs are separated with `|`, for example `A-01|B-02`. Current limits are 250,000 characters, 2,000 activities, task IDs up to 80 characters, and scenario delays from 0 to 60 whole days. Empty rows are ignored; duplicate headers/IDs, missing columns, invalid durations, missing predecessor IDs, cycles, and a disruption ID absent from the CSV are rejected.

This is **not** a native Primavera P6 XER/XML parser or live integration. Oracle documents P6 XML/XER as its exchange formats; this prototype needs a mapped CSV export in its own schema. The API checks graph structure but does not validate working calendars, actuals, lags, resources, contract terms or site conditions. Use synthetic or non-confidential data. The app does not save imported schedules in an application database, but this is not a certified secure data-ingestion service.

## Why this is a more useful interview demonstration

It contains two deliberately contrasting scenarios:

1. **Critical-path case:** adding 14 days to the synthetic structure activity moves handover from Day 119 to Day 133. A focused structural recovery crew recovers 6 days. At the editable illustrative assumption of ₹4.5 lakh per delay day and an assumed ₹8 lakh action cost, the calculated net value is ₹19 lakh.
2. **Schedule-float case:** adding 14 days to long-lead procurement does not move modeled handover beyond Day 119, because the facade/finishes chain still controls the finish. The model does not recommend paying ₹12 lakh to expedite procurement for finish-date recovery in that scenario.

These are deterministic examples built from made-up durations, dependencies, action effects and costs. **They are not claimed savings, probabilities, calibrated results, or estimates of Prestige's real project economics.** Their value is that the decision logic can be inspected, challenged and tested.

## What is implemented

- Interactive browser dashboard served by FastAPI.
- Editable disruption activity, delay length and daily-exposure assumption.
- Validated finish-to-start dependency graph with deterministic topological sorting, a CPM forward pass, backward pass, total float and tie-aware critical paths.
- Baseline versus disruption comparison, downstream impact trace and critical-chain display.
- Comparison of five hypothetical intervention options plus no action.
- Ranking by days recovered, action cost and modelled net value.
- A 3×3 deterministic assumption stress grid showing whether the preferred action remains stable when delay and daily-exposure assumptions change.
- One-click demo presets for the 14/15/16-day float threshold and a structural recovery comparison, so the interview demo does not rely on manual slider positioning.
- CSV schedule intake with server-side checks for required columns, duplicate IDs, durations, predecessor references and dependency cycles; accepted CSV schedules can be tested with a delay and inspected for float/critical-path changes.
- Pydantic input validation and tests for critical-path impact, schedule float, tied paths, non-topological input order, cycles, unknown predecessors, invalid durations and bounded critical-path output.
- Legacy /risk endpoint retained with a transparent rule-based snapshot score and bounded deviation indicator; it does not claim to run an ML anomaly detector.

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
| GET | /sample-schedule.csv | Download the synthetic CSV adapter example |
| POST | /api/schedule/analyze-csv | Validate a CSV network and compute baseline / one-delay CPM output |
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

Install test-only dependencies separately; production installs remain lean:

    pip install -r requirements-dev.txt
    python -m pytest -q

## Scheduling algorithm

For this proof of concept, relationships are simplified finish-to-start links and activity durations are positive numbers. The engine first validates unique task IDs, predecessor references, and durations; it then topologically sorts the graph and computes earliest start/finish using a forward pass. It computes latest finish/start in reverse order using a backward pass. Total float is `late start - early start`; tasks with zero float are treated as critical for this simple network. Ties are preserved as multiple critical paths rather than silently choosing one predecessor. Path counts are computed exactly, while the response materializes at most 256 paths to bound output size.

This matches the core CPM concepts documented by Oracle Primavera Cloud, which describes forward and backward passes, total float, critical paths and loop checking. It is not intended to reproduce Primavera's calendar, lag, constraint or resource-leveling behaviour.

## Model card and limits

- The decision engine is a **deterministic critical-path simulation**, not a trained delay-prediction model and not a causal model.
- The synthetic network has eight activities and simplified finish-to-start dependencies. It does not model working calendars, lag types, resource levelling, weather calendars, cash-flow, contract terms, uncertainty distributions or change orders.
- Intervention durations and costs are fixed illustrative assumptions. A real use case would require feasible alternatives approved by delivery teams and current cost inputs.
- Production requirements contain only FastAPI runtime dependencies; pytest and HTTPX live in `requirements-dev.txt` so they are not shipped with the public function.
- The recommendation stability panel varies the injected delay by ±4 days and the daily-exposure assumption by ±25% in a small deterministic grid. It is a sensitivity check, not a probability estimate, confidence interval, Monte Carlo run or proof of robustness beyond the tested range.
- The legacy /risk endpoint uses a transparent rule-based weighted snapshot score. Its field named `anomaly_score` is retained for API compatibility but contains a bounded heuristic deviation index—not an ML output, statistical anomaly score, or probability. Its weights and reference ranges are illustrative and unvalidated.
- No Prestige internal data or live Autodesk / Primavera / ERP / RERA connection is used. All project tasks and values are generic synthetic examples.
- A credible pilot would need permissioned schedule histories, stable task IDs, source timestamps, project calendars, actual planned/actual outcomes, back-testing, drift/error monitoring, access controls and human sign-off.

## Positioning for a real-estate technology discussion

Prestige publicly announced a three-year digital-transformation collaboration with Autodesk in April 2026. Autodesk also documents existing construction-risk features, while Oracle Primavera Cloud supports risk analysis connected to scheduling. The defensible proposal is therefore **not another dashboard**: it is to test whether a small, explainable decision-rehearsal layer could help delivery teams compare schedule recovery actions across approved data sources.

Any relevance to Prestige's actual processes remains a hypothesis to validate with its engineering-transformation and project-controls teams.

## Public research references

- Autodesk Research, Intelligent Construction: https://www.research.autodesk.com/projects/intelligent-construction/
- Autodesk Construction IQ documentation: https://help.autodesk.com/cloudhelp/ENU/Docs-Insight/files/Insight_Construction_IQ.html
- Oracle Primavera Cloud overview: https://www.oracle.com/in/construction-engineering/primavera-cloud-project-management/
- Oracle Primavera Cloud scheduling overview (CPM, backward/forward pass, total float and multiple paths): https://primavera.oraclecloud.com/help/en/user/88251.htm
- Oracle Primavera Cloud schedule project (loop checks and scheduling options): https://primavera.oraclecloud.com/help/en/user/88257.htm
- U.S. Government Accountability Office, Schedule Assessment Guide (GAO-16-89G): https://www.gao.gov/assets/gao-16-89g.pdf
- Prestige Group press-release index: https://www.prestigeconstructions.com/kn/news/2026/april

Prepared as a student proof of concept for a technology discussion. No affiliation with, endorsement by, or internal access to Prestige Group is implied.
