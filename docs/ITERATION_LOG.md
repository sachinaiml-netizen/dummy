# Project Impact Lab — Iteration Log

## 24-hour mission clock

- Mission start: 2026-10-09 19:15 IST (Asia/Kolkata)
- Mission deadline: 2026-10-10 19:15 IST (Asia/Kolkata)
- Current iteration: 6
- Time discipline: work occurs only when the user sends a new IMPROVE or FINALIZE message; no background execution is implied.
- Source of truth at iteration start: main at commit 9e0f0b5a78e93ddf0e566b89517056530c6d0e2b.

## Iteration 1 — public preview and deployment readiness

### Initial repository audit

- Latest main CI at the start of this mission: passing, run https://github.com/sachinaiml-netizen/dummy/actions/runs/37933693097.
- Application consists of a FastAPI service, a synthetic critical-path decision engine, a browser dashboard, and tests.
- The dashboard calls the FastAPI scenario API; it is not a truly standalone static page.
- The current repository name dummy and repository description about patient vitals do not match the construction-tech product.
- Deployment investigation found a Vercel scope mismatch: the connected Vercel context lists no accessible teams while the project list references an account ID that returns HTTP 403 when used as an explicit team scope. No public preview was verified at the start of the mission.

### First-pass opportunity ranking

| Rank | Opportunity | Business relevance | Technical value | Demo impact | Effort / risk | Decision |
|---|---|---:|---:|---:|---|---|
| 1 | Get a working, public, full-stack preview | Very high | High | Very high | Medium; account permissions may block it | Selected first |
| 2 | Correctness tests for float, critical paths, ties, invalid graph structures | High | Very high | High | Medium | Next candidate if deployment is blocked |
| 3 | Import and validate a synthetic schedule CSV with provenance and dependency checks | High | High | Very high | Medium | Defer |
| 4 | Add calendar/resource constraints or a more rigorous schedule algorithm | High | Very high | High | High risk of scope creep | Defer until correctness audit |
| 5 | Source-backed competitor matrix and pilot-validation protocol | High | Medium | High | Low-medium | Maintain in docs; improve later |

### Research links consulted

- Vercel, “How to ship a FastAPI app on Vercel”, published 2026-06-15: https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel
- GitHub Pages publishing sources: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- Render free web services and limitations: https://render.com/docs/free
- Autodesk Construction IQ documentation: https://help.autodesk.com/cloudhelp/ENU/Docs-Insight/files/Insight_Construction_IQ.html
- Oracle Primavera Cloud Risk Analysis: https://primavera.oraclecloud.com/help/en/user/88433.htm
- Oracle Primavera Cloud scheduling / critical paths and float: https://primavera.oraclecloud.com/help/en/user/88257.htm

### Change record

This log is itself part of iteration 1. Append timestamped entries rather than rewriting prior results. Every claim about deployment must distinguish configuration, successful build, HTTP availability, and end-to-end scenario verification.


## 2026-10-09 19:20 IST — Vercel bundle-size blocker and response

- A direct, unlinked Vercel deployment was created under the connected default account. The build failed with `LAMBDA_SIZE_EXCEEDED`: 239.84 MB reported bundle versus a 225 MB function limit.
- Vercel's error explicitly stated that the custom install command prevented automatic function bundle optimisation.
- Repository review identified NumPy and scikit-learn as runtime dependencies used only by the legacy snapshot-risk heuristic. The core Project Impact Lab scheduling engine does not require them, and the synthetic Isolation Forest was not validated against real project data.
- Selected fix: replace only that unvalidated synthetic anomaly detector with a bounded, explainable rule-based deviation index; preserve the /risk JSON field for compatibility; split test-only packages into requirements-dev.txt; let Vercel auto-detect and optimise installation by removing the custom install command on the next deployment.
- Verification at the time of this entry: the previous main CI passed, and the failed deployment itself is recorded as not usable. End-to-end public preview remains unverified until a subsequent build and live route checks pass.


## 2026-10-09 19:25 IST — public preview verified

- Runtime slimming and test-dependency split merged to main at commit 5d735f6cb75850a5096a28393585a29ef8e28725; CI for the corresponding branch passed.
- First deployment failed at 239.84 MB because the custom install command disabled Vercel's bundling optimisation. The app's unvalidated synthetic Isolation Forest was removed from the legacy snapshot endpoint and replaced with a documented rule-based deviation indicator; NumPy/scikit-learn were removed from production requirements and test-only dependencies moved to requirements-dev.txt.
- A second direct deployment used Vercel project prj_l1bNrbcs5CKYNy1nVnA3915GZH8O and returned READY. Its public alias is https://project-impact-lab.vercel.app/.
- Public GET checks succeeded: / returned HTML titled "Project Impact Lab | Decision rehearsal"; /health returned status=ok; /api/scenario returned valid JSON with baseline_finish_day=119, shocked_finish_day=133, shocked_slip_days=14, recommended action structural_recovery, six days recovered and illustrative net value ₹19.0L; /api/catalog returned the eight-task and six-option synthetic catalog.
- The project-level SSO protection was disabled so the public preview is accessible without a Vercel login. Public routes were fetched again successfully after that change.
- Runtime behavior was verified through a live public fetch and API responses; POST /api/scenario and invalid-input behavior are covered by passing automated tests. A human-operated, click-by-click browser session was not performed in this iteration, so do not claim that a screen-recorded interaction test passed.
- The preview is a manual source deployment, not GitHub-linked, because the connected Vercel account lacks a GitHub Login Connection. Future main changes will not automatically appear until a GitHub connection is established or a new deployment is created. No paid add-on, database, or custom domain was purchased; connected Vercel billing details were not accessible, so account-wide plan status is not certified.


## Iteration 2 — CPM correctness and tie handling

- Iteration trigger received: approximately 2026-10-09 20:12 IST; mission deadline: 2026-10-10 19:15 IST. The original 24-hour clock started 2026-10-09 19:15 IST. At iteration 2 start, approximately 23 hours remained. Work is only triggered by an explicit IMPROVE or FINALIZE message.
- Live main at iteration start: d9500aa067bf0644cb6b449d2e5907fb20e05c6b. CI passed: https://github.com/sachinaiml-netizen/dummy/actions/runs/37941737668. Existing public preview checked READY at https://project-impact-lab.vercel.app/.
- Official research used to scope the fix: Oracle Primavera Cloud Scheduling Overview (https://primavera.oraclecloud.com/help/en/user/88251.htm) states that CPM runs forward and backward passes, calculates total float and identifies critical paths; Oracle's Schedule a Project page (https://primavera.oraclecloud.com/help/en/user/88257.htm) documents loop checking and cautions that relationship settings, calendars and resource levelling affect scheduling. GAO Schedule Assessment Guide (GAO-16-89G): https://www.gao.gov/assets/gao-16-89g.pdf.
- Critical finding: the earlier display selected a single predecessor in a tie and the engine exposed no total-float value. This could conceal a second controlling path and provide a misleading explanation near the float threshold.
- Selected fix: generic validated CPM analyzer, deterministic topological sort, backward-pass dates and total float, all tied critical paths with exact path count and bounded materialized paths. Added activity-level float outputs for baseline, delayed and recommended schedules and changed the dashboard to display float and every returned critical path.
- Five ranked opportunities for iteration 2: (1) correct CPM float/tied-path engine (selected); (2) validate imported dependency graphs and schedule fields; (3) display critical and near-critical path margin; (4) create reproducible scenario fixtures and API contract tests; (5) complete repository branding and automatic deployment setup (blocked by missing GitHub Login Connection in Vercel).
- Verification completed: PR #7 merged to main at commit `6d7f6e19cb30a04c24b95f824f29f8f6e638e2a6`; the main-branch CI run passed and its test log reports 25 passed, 1 existing Starlette deprecation warning. Live deployment `dpl_7r79CpxQi7Q6PVGU9isnEpeSCGSg` reached READY and is serving https://project-impact-lab.vercel.app/ from that commit.
- Public route checks after redeployment passed for `/`, `/health`, `/api/scenario`, and `/api/catalog`. The HTML contains the total-float column; the live default scenario response includes total float on each activity, critical-path arrays/counts, and baseline float of 15 days for procurement / 6 days for MEP. The critical-path tie case at a 15-day procurement delay is covered by automated tests, which verify two tied critical paths. The live site was not submitted a POST from an external browser automation session in this iteration; POST input validation remains verified by CI. Deployment remains manual and is not automatically connected to GitHub.


## Iteration 3 — interview-first problem framing and Float-Burn Watch

- Iteration trigger received at 2026-10-09 20:42:49 IST; original mission deadline remains 2026-10-10 19:15 IST (approximately 22 hours 32 minutes remained at start).
- Main at iteration start: 487a43f7ed43cbac3523a72f324c2922e8858f8f; main CI passed. Public deployment was READY but still served the CPM code from commit 6d7f6e19cb30a04c24b95f824f29f8f6e638e2a6, because deployment is manual.
- Research finding: broad claims such as “AI risk dashboard”, “digital twin”, or “critical-path analysis” are not differentiated. Autodesk Construction IQ already prioritises risk using analytics/ML; Oracle Primavera calculates CPM, total float and multiple float paths; Bentley promotes 4D and infrastructure digital twins. CSCEC describes integrated industrial software, smart factories and intelligentised sites. CCCC describes IoT-enabled digital-twin decision support for a reservoir. The U.S. GAO Schedule Assessment Guide explicitly advises identifying near-critical paths. Sources are linked in docs/PROBLEM_STATEMENT.md and docs/COMPETITIVE_RESEARCH.md.
- Selected improvement: focus on one explainable scenario—float burn. For procurement with 15 days baseline total float: +14 days leaves 1 day float and does not move handover; +15 exhausts float and creates a tied second critical path; +16 moves modeled handover one day. Add response fields for baseline/scenario float and consumed buffer, generate threshold-specific explanations, highlight near-critical or exhausted-float activities in the UI, and add regression tests.
- Added interview preparation: docs/SIX_HOUR_LEARNING_GUIDE.md (5h40m plan), docs/PROBLEM_STATEMENT.md, docs/COMPETITIVE_RESEARCH.md. The guide explicitly coaches truthful description of AI-assisted coding and explains the frontend/backend, APIs, CPM algorithm and limitations.
- Verification completed: PR #9 merged to main at commit 4a81148255c48298ae5c8342c9375b3ca014bc2c. The merged-main CI run passed with 29 tests and one existing Starlette deprecation warning: https://github.com/sachinaiml-netizen/dummy/actions/runs/37950892103.
- A new manual Vercel deployment (dpl_6ViicUkpNYwdi9R2ucdGvzCk13Lc) reached READY and serves commit 4a811482 at https://project-impact-lab.vercel.app/. Public fetch checks passed for the page, /health and /api/scenario. The page includes the new Float-Burn Watch problem statement. The default API response includes the new disrupted-activity float fields; the procurement 14/15/16-day thresholds and explanation strings are covered by the passing automated tests.
- Verification limitation: no external live POST browser session was run. The public UI and GET endpoints were fetched, and POST scenario cases were verified in CI. No claim is made that the Prestige internal workflow or a competitive gap has been proven; both remain hypotheses to test with authorised project-controls users.
- The deployment is still manually uploaded and is not linked to GitHub because the connected Vercel account has no GitHub Login Connection. Repository-level rename is not exposed by the connected GitHub toolset, so repository name remains dummy.


## Iteration 4 — threshold demo and Prestige-facing explanation

- Trigger: 2026-10-09 approximately 21:55 IST. Mission began 2026-10-09 19:15 IST; deadline remains 2026-10-10 19:15 IST, leaving approximately 21 hours 20 minutes at iteration start. Work occurs only when the user sends an instruction; there is no background execution.
- Source-of-truth audit: main commit f03591bd6228a4baee4e842fed0031b64485704e; main CI passed. The public Vercel deployment is a manual deployment and must be rechecked after this branch is merged and redeployed.
- New research checked: Oracle Primavera documentation confirms support for multiple float paths and response-action effectiveness / finish-cost impact; Autodesk Construction IQ documents ML risk prioritisation; CSCEC's September 2026 official technology showcase describes 5G smart tower cranes, monitoring equipment, drones and BIM+GIS/digital-tunnel platforms; CCCC's official 2025 article documents an IoT/digital-twin reservoir decision platform; April 2026 trade press reported a three-year Prestige–Autodesk collaboration and 4D/5D context. Prestige-specific details are labelled secondary-source reporting, not internal confirmation.
- Five opportunities ranked: (1) create one-click 14/15/16-day float-threshold presets for a reliable interview demo (selected); (2) add validated schedule CSV import; (3) record a real browser click-through and POST request test after deployment; (4) update competitive evidence and the Prestige-specific fit with source quality stated; (5) fix repository branding and connect Vercel to GitHub (the account connection is a known blocker).
- Implemented this cycle: three direct procurement-threshold buttons plus the existing structural-recovery preset; responsive two-column layout; test asserts the buttons and helper statement are served; interview/playbook and six-hour guide updated to use the exact UI labels; competitive research updated with source-backed examples and a caveat that Prestige's Autodesk relationship is described in secondary trade-press reporting.
- Value rationale: the user can show the exact threshold progression in under a minute without changing a slider manually. This makes the central problem easier to explain without adding a new algorithm or claiming novelty not present in commercial tools.
- Verification completed: PR #11 merged into main at `b278fd16c49507ffbb6268b44b2bf708a957352b`; feature-branch CI and main CI both passed with 30 tests passed and one existing Starlette deprecation warning. Main CI: https://github.com/sachinaiml-netizen/dummy/actions/runs/37961095913.
- Redeployed the full FastAPI app from commit `b278fd16c49507ffbb6268b44b2bf708a957352b`. Vercel deployment `dpl_GSRENuDEBTJyCGf41xj56FEp8eNm` reached READY at https://project-impact-lab.vercel.app/.
- Public route checks passed for `/`, `/health`, and `/api/scenario`. Public HTML fetch confirms the Float-Burn Watch problem statement and new threshold workflow content; automated test `test_dashboard_exposes_one_click_float_threshold_scenarios` checks the three button IDs, labels and explanation are served by FastAPI. Existing API tests cover 14-, 15- and 16-day procurement scenarios, including 1 day of float, zero float/tied paths, and one-day handover slip.
- Attempted a live browser click-through to exercise the three buttons, but the metered browser tool did not start because its wallet balance was negative. No top-up was made, consistent with the no-paid-services constraint. Therefore the actual click sequence is **not verified by external browser automation**; CI and public GET checks passed. Do not represent this as a successful click-through.
- Deployment remains manually uploaded, not GitHub-linked. The preview URL is current to this iteration's runtime commit, but later code changes will require another manual deployment.


## Iteration 5 — interview clarity and explainability

- Trigger: user explicitly asked to keep improving the construction interview project while keeping the problem statement and architecture learnable in five to six hours.
- Research basis carried forward: Oracle Primavera Cloud already supports CPM, total float and multiple float paths; Autodesk Forma/Construction IQ documents construction risk analytics; CSCEC and CCCC publicly document intelligent construction, BIM/GIS, IoT and digital-twin decision support. Existing products mean we must not claim the underlying algorithm or broad capability is globally unique.
- Product decision: keep Float-Burn Watch as the focused feature. Its defensible hypothesis is a very short, inspectable threshold explanation (14/15/16-day procurement delay), not replacing a commercial scheduler.
- Implemented: added `docs/INTERVIEW_ONE_PAGE.md`, with the 45-second problem statement, synthetic example, frontend/backend data flow, file map, CPM definitions, value formula, competitive honesty, AI-assisted development disclosure, limitations and likely interview questions. README now links to this one-page guide first.
- Validation: documentation-only change; CI should pass before merge. No application code or live deployment changes are required for this iteration. The live preview remains manually deployed and is not GitHub-linked.


## Iteration 6 — configurable CSV schedule intake

- Trigger: user sent IMPROVE after the interview-clarity iteration. Mission clock began 2026-10-09 19:15 IST and ends 2026-10-10 19:15 IST; approximately 20 hours 45 minutes remained when this iteration began.
- Source-of-truth audit: main at start was `f4f885aa7a0ecdca6256db2b6672635b5894f54f`, with passing main CI. Current main already includes the new CSV UI/API edits from this cycle's first write attempt, but the sample file and CSV regression tests are not yet merged. This iteration uses a new finishing branch based on current main and must not treat the feature as complete until the missing assets/tests/documents are merged and CI passes.
- Official research: Oracle Primavera Cloud documents importing/exporting P6 projects using P6 XML/XER rather than this prototype's CSV schema: https://primavera.oraclecloud.com/help/en/user/95912.htm and https://primavera.oraclecloud.com/help/en/user/191098.htm. GAO's Schedule Assessment Guide emphasizes well-constructed, logically linked schedules: https://www.gao.gov/products/gao-16-89g.
- Five ranked opportunities: (1) complete and test the CSV schedule intake so the app can analyse a configurable task network (selected); (2) verify live browser interactions including POST; (3) fix repository branding and automatic GitHub deployment (connection remains blocked); (4) add schedule-data provenance and clearer warnings; (5) improve accessibility and front-end JavaScript tests.
- Critical finding: the app was still limited to a hard-coded eight-activity network. This weakened the claim that the workflow could be used to test a different task network. At the same time, pretending to import P6 exchange files would be misleading.
- Implemented in the feature branch: bounded generic CSV adapter with required/optional columns; validation for missing/duplicate headers, row fields, unique IDs, duration values, predecessor references and dependency cycles; optional activity-delay scenario using the same CPM engine; a downloadable synthetic CSV sample; a dashboard flow for selecting a local CSV, validating it, selecting an activity and running a delay; tests for threshold behaviour and malformed CSVs; docs explaining API, input format, data provenance and the explicit lack of native P6 XER/XML support.
- Design simplification: use Python's standard-library CSV parser and the existing CPM engine. No new runtime package, machine-learning model, database or live integration was added.
- Verification completed: PR #14 merged to main at `dd9c775bbd22bcf4ee25d9228ccb9bfc07d7a229`; main CI passed with 41 tests passed and one existing Starlette deprecation warning: https://github.com/sachinaiml-netizen/dummy/actions/runs/37968646019. Vercel deployment `dpl_8HZdBg1QyBmYnqxXU8AUWXqyaB2n` reached READY and serves that commit at https://project-impact-lab.vercel.app/. Public GET checks passed for `/`, `/health`, `/api/scenario`, `/sample-schedule.csv` and `/openapi.json`; the OpenAPI schema lists `POST /api/schedule/analyze-csv`. No external live POST was issued, so do not claim that an external POST interaction was manually verified; the 14/15/16-day CSV calculations and malformed-input handling are covered by CI.
- Process note: an early write pass omitted the branch argument for several files, creating partial CSV implementation changes on `main` before tests and the sample asset were complete. No deployment was made from that partial state. A finishing branch was cut from the exact current main state, regression tests exposed and fixed optional-column handling, and the completed change was merged only after the 41-test run passed.
- Deployment limitation persists: Vercel is a manual source deployment and not linked to GitHub because the connected account lacks a GitHub Login Connection. Later main changes require a fresh deployment.


## Iteration 7 — interview readiness gate

- Trigger: user requested another improvement after the validated CSV schedule-intake release.
- Audit finding: the README already links to a detailed problem statement, interview one-page, competitive research and a 5h40m study plan. Creating a duplicate pitch document would add no value. The remaining practical risk is that the user can read the materials but still cannot independently explain the threshold example or distinguish deterministic CPM from AI-assisted coding.
- Implemented improvement: add a 10-question oral readiness gate and explicit pass criteria to docs/SIX_HOUR_LEARNING_GUIDE.md. The questions cover problem framing, 14/15/16-day float burn, CPM, frontend/backend, CSV limits, AI honesty, synthetic data, illustrative cost arithmetic, competitive positioning and real-pilot evidence.
- A live click-through browser test was attempted via the available browser automation, but it did not start because the connected automation wallet has a negative balance (-$0.23). No charge or top-up was initiated. This is an external verification blocker, not an application failure; the live GET routes and automated POST tests remain available as previously recorded.
- Verification pending: CI for this documentation-only change, merge and a final check that the public preview remains accessible. No application code or runtime behaviour is changed in this iteration.


## Iteration 8 — decision brief export and release verification

- Trigger: another explicit Improve after Iteration 7. Main at this iteration's code-change start: `61dbf1d6a307b80278bac5cf22081ab5026b5f55`, including the merged CSV intake boundary tests from PR #16.
- Finding: the CSV workflow showed a scenario in the dashboard but had no portable decision summary. The right-sized improvement is a local text export, not a database or a larger project-controls platform.
- Implemented: the CSV analysis result now has a “Download decision brief (.txt)” control. The generated brief includes selected activity/delay, baseline and scenario finish, handover slip, float consumed and remaining, critical-path lists/counts, activity-level finish/float trace, input-format caveat, validation scope, and explicit limits such as calendars, lags, resources, contracts and site conditions. It clearly identifies the output as a deterministic what-if scenario rather than a prediction or approved recovery plan. The download is generated in the browser; it does not add schedule persistence or runtime dependencies. The UI warns that task names from an uploaded CSV may be included in the exported text.
- Test and build guard: added `test_decision_brief_export_is_visible_and_carries_model_limits` in `tests/test_csv_schedule.py`; added a Node 20 `node --check` step for the dashboard's inline JavaScript in `.github/workflows/ci.yml`.
- Merged: PR #18 (https://github.com/sachinaiml-netizen/dummy/pull/18) was squash-merged to main at `fe116d38b6b3fbe09016d6f4b4632fa7125b344e`.
- CI evidence: PR-head test and syntax-check runs passed; post-merge main CI passed at https://github.com/sachinaiml-netizen/dummy/actions/runs/38011306869 and the main Pages build passed at https://github.com/sachinaiml-netizen/dummy/actions/runs/38011306378.
- Deployment attempt and recovery: a Git-source deployment attempt failed with Vercel `git_info_fail`, consistent with the existing project/Git connection limitation. A second production deployment was created using the explicit UTF-8 source bundle fetched from that exact main SHA. Vercel deployment `dpl_9XwNd61sTVQGpAsct7U3zR8hG2Gk` reached `READY` and carries the aliases including https://project-impact-lab.vercel.app/. Vercel's deployment-events endpoint returned 403, so deployment logs were not inspected; ready-state metadata and live HTTP checks were used instead.
- Live checks: the production home page contains the new download control and data-sharing warning; `/health` returned `status=ok`; `/api/scenario` returned a valid scenario JSON response; `/sample-schedule.csv` served the expected eight-task sample; and `/openapi.json` responded. This confirms the deployed asset and key GET routes. It does not confirm a real browser download or external CSV POST.
- Verification limit: the browser automation for the click-through CSV workflow did not start because the connected automation wallet balance was `-$0.23`. No top-up was initiated. An external POST test also could not be performed from the available container network. The CSV POST success/invalid-input/float-threshold behaviours remain covered by the passing automated test suite; live end-to-end browser interaction remains unverified.
- Next target: when browser automation is available, execute the public workflow end-to-end: load sample, validate eight activities, run `PR-01` with a 14-day delay, confirm Day 119 and one day of remaining float, then download and inspect the decision brief. Follow up separately on a supported Vercel GitHub connection to remove the manual source-bundle deployment path.


## Iteration 9 — make the first screen match the float-burn thesis

- Trigger: user asked for another prototype improvement after checking live output and schedule-import behaviour.
- Review finding: the public home page's explanatory text teaches the procurement threshold (+14 days leaves 1 day of float), but the initial dashboard selected the first catalog item (approval package) and showed a +14-day handover slip. That mismatch made the first screen contradict the main example before a user clicked the threshold buttons.
- Change: set the initial browser selection and default scenario API response to procurement activity PR-01 with a 14-day delay. The expected first view now teaches one coherent result: baseline finish Day 119, scenario finish Day 119, 14 of 15 float days consumed, one day remaining, and no paid recovery action justified by the modeled scenario. The structural +14-day recovery case remains available as an explicit button.
- Regression coverage: update the engine/API default to procurement and add assertions for the default API result and the UI's selected activity. Existing CSV tests already cover a valid 8-task sample and the 14/15/16-day boundary cases, including the tied critical paths at 15 days and the one-day handover slip at 16 days.
- External research check: Microsoft Project's official documentation defines total slack as the time an activity can slip before affecting project finish and notes that the critical path can change; Oracle Primavera Cloud documents forward/backward CPM passes and total-float calculation. Sources: https://support.microsoft.com/en-us/project/manage-your-project-s-critical-path and https://primavera.oraclecloud.com/help/en/user/88251.htm.
- Verification status at edit time: public GET checks confirmed the live home page, health route, sample CSV and OpenAPI contract. The sample CSV contains 8 valid tasks and the PR-01 predecessor network used by the threshold tests. An external live POST/browser upload could not be completed from this session because the shell has no DNS/network access and metered browser automation is out of credits. Do not claim a live upload or browser download succeeded; rely on CI for POST behaviour until a browser test can be run.
- Release gate: run branch CI, review output and merge only if all checks pass. The production deployment remains manual and must be separately redeployed and rechecked after merge.


## Iteration 10 — validate the generated decision-brief text

- Trigger: after the default scenario fix, review the actual public API output and the CSV export code for the next highest-value validation gap.
- Live review: the production deployment is READY on main commit `80d6f4dc7e21d7e96a3267e46d518c826e81cb6a`. `/health` returns status=ok; `/api/scenario` returns the expected PR-01 +14-day result (Day 119 baseline and scenario, 14/15 float days consumed, 1 day remaining, no paid action); `/sample-schedule.csv` serves eight linked activities; `/openapi.json` exposes the CSV analysis POST contract.
- Remaining gap: prior regression coverage only checked that the download button and disclaimer strings existed in HTML. It did not execute the text-brief builder or assert that the exported notes contained the expected scenario values.
- Implemented: add a Node test that extracts and executes the actual browser-side `buildCsvDecisionBrief` function against a valid synthetic scenario payload and a baseline-only payload. Assert the brief includes activity count, selected activity/delay, float consumed, baseline/scenario finish, handover slip, critical paths, validation scope, native-P6 format caveat, model limits and no-persistence warning. Run this test in CI alongside the existing inline JavaScript syntax check and Python API/CPM suite.
- Verification boundary: the public POST upload and actual browser download still cannot be manually exercised from this session: the shell has no DNS/network access and the connected browser automation wallet is out of credits; the Opera browser connector is not connected. This iteration adds executable regression coverage for the export output but does not convert that limitation into a claimed live browser test.
- Release gate: PR CI must pass; after merge, redeploy the exact main source bundle and recheck production health, default scenario and sample CSV.


## Iteration 11 — browser-level upload, threshold, export and escaping test

- Review finding: backend TestClient coverage validates the CSV endpoint and threshold math, while the previous Node check executed the decision-brief text builder. Neither exercised the real file input, user clicks, browser download event or rendered CSV task labels.
- Change under review: add a headless Playwright workflow to CI using the app's own `/sample-schedule.csv` route. The test downloads the sample bytes, uploads those bytes through the browser file input, validates eight activities, runs a 14-day PR-01 delay, and checks Day 119 / one day of remaining float. It also clicks the 15-day and 16-day quick cases, downloads the decision brief and inspects its content, then confirms an HTML-looking task name is rendered as text rather than a DOM element or script.
- CI setup: Node 20, pinned Playwright package, Chromium installation, a 15-minute job timeout, and the existing dashboard syntax / decision-brief / Python tests remain in place.
- Test scope: this is an automated browser test of the same app code launched locally inside GitHub Actions. It is stronger than a DOM-string test but is not a manual click-through against the public deployment. Production GET routes were checked separately; public browser automation remains blocked by the connected automation wallet having a negative balance.
- Release gate: verify Playwright/Chromium installation and the browser workflow on the branch CI; merge only if the complete workflow passes. No runtime feature change is intended by this test-only iteration.


## Iteration 12 — invalid CSV upload must invalidate prior output

- Review finding: browser E2E now proves a valid uploaded schedule can be analysed and exported, plus CSV names are escaped safely. The remaining UI failure path worth guarding is a user who first gets a valid result, then selects a malformed schedule with a missing predecessor.
- Change under review: extend the same real-browser flow with a CSV referencing a missing predecessor. Assert the UI displays an explicit validation error, hides the prior analysis, disables scenario execution, and hides the decision-brief download control so an old result cannot be mistaken for the failed upload.
- This is a test-first validation iteration; no product runtime code changes are intended unless the test exposes a defect.
- Release gate: wait for CI's browser workflow plus the full Python regression suite. If the invalid-upload state does not meet these assertions, fix the UI state-handling code before merging.


## Iteration 14 — synthetic-trained risk proof model

- User request: train a synthetic model for a future project-risk proof point, make the data and training process as useful/reproducible as possible, and keep the interface understandable.
- Audit finding: the existing `POST /risk` route is a fixed weighted heuristic. It is not a trained ML model, and its weights are not calibrated to real construction outcomes. Replacing it in place would break compatibility and risk overstating the model, so a separate route was selected.
- Model: standardized logistic regression implemented in pure Python; no new runtime ML dependencies. Features are planned progress, positive schedule gap, positive budget variance, vendor delay days, unresolved issue count and quality-defect count. Project IDs are not features.
- Training corpus: 60,000 reproducibly generated synthetic snapshots (42,000 train / 9,000 validation / 9,000 held-out test) generated from `construction-risk-generator-v1` with seed 20261010. The synthetic target is sampled from an invented risk formula; it is not real project-outcome data. Committed artifact: `app/risk_model.json`.
- Held-out synthetic metrics: ROC-AUC 0.7961; accuracy 0.7402; precision 0.7073; recall 0.5658; F1 0.6287; Brier 0.1744; majority-class accuracy 0.6113. These are measures of fit to that synthetic generator only, not real-world quality indicators. The UI/API repeat this warning.
- Product changes in this branch: add `POST /api/risk/proof-model`, a simple telemetry form in the existing dashboard, the score band and per-feature contributions, model test metrics, a stdlib training script, model unit tests, retraining documentation and source links.
- Real-data path: offline CSV training requires `project_id`, `snapshot_date`, the six telemetry fields and an observed `target_high_risk_30d` value. It uses a time-ordered 70/15/15 split with a 30-day embargo before validation/test cutoffs; it does not make labels from the telemetry. Candidate artifacts are written to a user-chosen file, not automatically installed in the public app.
- Research basis: Google advises evaluating on separate representative data and warns about train/test contamination and train-serving skew; NIST calls for explicit test/evaluation/validation and external-validity assessment. Sources: https://developers.google.com/machine-learning/crash-course/overfitting/dividing-datasets ; https://developers.google.com/machine-learning/guides/rules-of-ml/ ; https://www.nist.gov/itl/ai-risk-management-framework ; https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/.
- Release gate: validate the synthetic artifact can be reproduced, run API/model tests, test the dashboard form in Playwright and pass the existing CPM/CSV regression suite. This branch is not deployed to production until CI passes and it is merged/redeployed.
- Non-negotiable limitation: no claim is made that synthetic training can make the model reliable on Prestige's real data by itself. Real use requires an agreed outcome definition, approved labelled history, temporal back-testing, calibration, subgroup/error review and human approval.
