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

## 4. Synthetic-trained risk proof model

A separate optional model sits beside—rather than replacing—the deterministic CPM engine. `POST /api/risk/proof-model` scores a telemetry snapshot using a standardized logistic-regression artifact in `app/risk_model.json`. It returns a synthetic-model score, provisional score band, per-feature logit contributions and same-generator held-out metrics. The current artifact contains 60,000 generated examples (42,000 train / 9,000 validation / 9,000 test) and does not use Prestige data.

The stdlib-only training pipeline is `scripts/train_risk_model.py`. Its synthetic mode produces reproducible examples and an invented probabilistic target; its optional CSV mode requires already-labelled historical snapshots with `project_id`, `snapshot_date`, current telemetry fields and `target_high_risk_30d`. It uses a chronological split with a 30-day embargo by default, excludes project IDs from model features, and reports accuracy, precision, recall, F1, ROC-AUC, Brier score, a majority baseline and a confusion matrix. It does not create observed outcome labels from input features.

**Validity boundary:** current reported ROC-AUC and accuracy measure fit to the synthetic generator only. They are not external validation, real-world calibration or evidence of performance on Prestige. For a real candidate, project controls must define the event and horizon (for example, an agreed adverse milestone/cost/quality outcome within 30 days of snapshot), label historical outcomes, check temporal and project-level generalization, review false negatives/positives and subgroup performance, and retain human decision authority. The thresholds 35% and 65% are UI demo bands, not operational thresholds.

This workflow follows common ML practice to keep training and test data separate and to ensure the test set resembles future use, and NIST's emphasis on validity, reliability and external validity: [Google's dataset-splitting guidance](https://developers.google.com/machine-learning/crash-course/overfitting/dividing-datasets), [Google's ML Rules](https://developers.google.com/machine-learning/guides/rules-of-ml/), [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework), and [NIST AI trustworthiness characteristics](https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/).

## 5. Production evolution

A real pilot should use approved historic project snapshots and schedules. Calibrate any scoring thresholds with domain experts, evaluate against held-out time periods, compare against a simple baseline, and report false-positive/false-negative behaviour before presenting any model as validated. Preserve feature provenance, thresholds, model/version metadata and human review records.
