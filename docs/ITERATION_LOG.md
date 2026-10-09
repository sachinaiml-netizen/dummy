# Project Impact Lab — Iteration Log

## 24-hour mission clock

- Mission start: 2026-10-09 19:15 IST (Asia/Kolkata)
- Mission deadline: 2026-10-10 19:15 IST (Asia/Kolkata)
- Current iteration: 5
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
