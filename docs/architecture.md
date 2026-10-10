# Architecture Notes

## 1. Primary decision engine

The primary Project Impact Lab engine is deterministic Critical Path Method (CPM) logic on a directed acyclic activity network with simplified finish-to-start relationships. It calculates a baseline dependency network, injects a scenario delay, recomputes the finish date, and evaluates explicitly parameterized recovery actions. It is not an ML forecast.

### Schedule pass details

1. Validate non-empty unique activity IDs; positive finite durations; predecessor lists; unique dependencies; and references to activities that exist.
2. Topologically sort the graph. Reject cycles rather than making up an order.
3. Forward pass: early start is the maximum early finish of the predecessors; early finish is early start plus duration. Source tasks start at day zero.
4. Set the modeled project finish to the maximum early finish across all terminal tasks.
5. Backward pass: terminal late finish is the modeled project finish; all other late finishes are the minimum late start among successors. Late start is late finish minus duration.
6. Total float is late start minus early start. For this simplified CPM model, zero-float tasks are critical. Edges are critical only where the predecessor's early finish meets the successor's early start and both tasks have zero float.
7. Preserve all tied critical paths. The exact path count uses dynamic programming; at most 256 actual paths are included in an API response to avoid unbounded response size.

The product's currently emphasised workflow is **Float-Burn Watch**: show how a reported delay consumes an activity's original total float and whether the activity becomes co-critical or pushes the modeled project finish. This is a plain-language layer over CPM, not a new scheduling method. The workflow's novelty/value for any specific company is unverified. See [Problem Statement](PROBLEM_STATEMENT.md) and [Competitive Research](COMPETITIVE_RESEARCH.md).

This core logic follows the basic forward/backward-pass and total-float concepts documented in Oracle Primavera Cloud's [Scheduling Overview](https://primavera.oraclecloud.com/help/en/user/88251.htm). Oracle separately documents loop checks and notes that calendars, relationship lags and resource levelling affect real project schedules: [Schedule a Project](https://primavera.oraclecloud.com/help/en/user/88257.htm). Project Impact Lab does not implement those features.

## 2. CSV schedule adapter

The `POST /api/schedule/analyze-csv` route accepts JSON containing CSV text, an optional task ID to delay and a delay from 0 to 60 days. The documented required columns are `task_id`, `task_name`, `duration_days` and `predecessors`; `owner` and `stream` are optional. Multiple predecessor IDs are separated by `|`.

The adapter uses Python's standard-library CSV parser, applies size and activity-count limits, rejects duplicate headers and IDs, missing required values, invalid durations, unknown predecessor IDs and cycles, then runs the shared `analyze_schedule` CPM engine on baseline and scenario durations. The result contains finish dates, float by activity, critical-path lists/counts and a human-readable summary. Uploaded contents are not written to an application database.

**Boundary:** this is a small CSV schema, not a native Primavera P6 XER/XML parser. Oracle documents P6 XML/XER as exchange formats ([import/export overview](https://primavera.oraclecloud.com/help/en/user/95912.htm)). A production pilot would require an authorised export/mapping layer, validation of schedule calendars and constraints, and project-controls review.

## 3. Legacy snapshot-risk endpoint

The separate `POST /risk` endpoint returns a weighted score from schedule gap, budget variance, vendor delay, unresolved issues and quality defects. A bounded rule-based deviation index is retained under the legacy response key `anomaly_score` for compatibility.

The deviation index normalizes each signal against an illustrative reference range, caps each value at 1, and combines them using fixed weights totalling 1. It is not an Isolation Forest, trained anomaly detector, confidence score, or probability. The weights and ranges have not been calibrated against real construction outcomes.

This rule-based design is intentional: fitting an Isolation Forest to synthetic samples creates no evidence of real-world anomaly detection and adds substantial runtime dependencies without strengthening the project's primary schedule-decision demonstration.

## 4. Experimental synthetic risk classifier

A separate POST /risk-model endpoint loads a versioned logistic-regression artifact from static/synthetic_risk_model.json. scripts/train_synthetic_risk_model.py reproducibly generates 115,000 rows: 70,000 training; 15,000 validation; 15,000 same-generator test; and 15,000 shifted synthetic stress-test rows. The artifact is checked in CI with the --check flag. The current features are schedule gap, positive budget variance, vendor delay days, open issues and quality defects.

This is a trained model, but its target is a simulated label, not a verified construction outcome. Its metrics do not validate generalisation to Prestige or another real developer. POST /risk remains the separate rule-based legacy endpoint. See SYNTHETIC_RISK_MODEL.md for the model card and the real-data validation plan.

## 5. Production evolution

A real pilot should use approved historic project snapshots and schedules with well-defined future outcome labels. Split by whole project and later time periods to avoid leakage, calibrate thresholds with project-controls experts, compare against simple baselines, and report calibration, false-positive/false-negative behaviour and drift. Preserve feature provenance, thresholds, model/version metadata and human review records.
