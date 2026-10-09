# Project Impact Lab — Iteration Log

## 24-hour mission clock

- Mission start: 2026-10-09 19:15 IST (Asia/Kolkata)
- Mission deadline: 2026-10-10 19:15 IST (Asia/Kolkata)
- Current iteration: 1
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

- Start: 2026-10-09 19:15 IST; deadline: 2026-10-10 19:15 IST; this cycle is executed only on the user's explicit IMPROVE command. Approximately 23.5 hours remain as iteration 2 begins.
- Live main at iteration start: d9500aa067bf0644cb6b449d2e5907fb20e05c6b. CI passed: https://github.com/sachinaiml-netizen/dummy/actions/runs/37941737668. Existing public preview checked READY at https://project-impact-lab.vercel.app/.
- Official research used to scope the fix: Oracle Primavera Cloud Scheduling Overview (https://primavera.oraclecloud.com/help/en/user/88251.htm) states that CPM runs forward and backward passes, calculates total float and identifies critical paths; Oracle's Schedule a Project page (https://primavera.oraclecloud.com/help/en/user/88257.htm) documents loop checking and cautions that relationship settings, calendars and resource levelling affect scheduling. GAO Schedule Assessment Guide (GAO-16-89G): https://www.gao.gov/assets/gao-16-89g.pdf.
- Critical finding: the earlier display selected a single predecessor in a tie and the engine exposed no total-float value. This could conceal a second controlling path and provide a misleading explanation near the float threshold.
- Selected fix: generic validated CPM analyzer, deterministic topological sort, backward-pass dates and total float, all tied critical paths with exact path count and bounded materialized paths. Added activity-level float outputs for baseline, delayed and recommended schedules and changed the dashboard to display float and every returned critical path.
- Five ranked opportunities for iteration 2: (1) correct CPM float/tied-path engine (selected); (2) validate imported dependency graphs and schedule fields; (3) display critical and near-critical path margin; (4) create reproducible scenario fixtures and API contract tests; (5) complete repository branding and automatic deployment setup (blocked by missing GitHub Login Connection in Vercel).
- Verification pending at log write: new branch/PR CI must pass before merge; public preview must be redeployed from the merged source and rechecked. No live deployment update is assumed from a GitHub merge.
