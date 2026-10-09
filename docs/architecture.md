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

## 2. Legacy snapshot-risk endpoint

The separate `POST /risk` endpoint returns a weighted score from schedule gap, budget variance, vendor delay, unresolved issues and quality defects. A bounded rule-based deviation index is retained under the legacy response key `anomaly_score` for compatibility.

The deviation index normalizes each signal against an illustrative reference range, caps each value at 1, and combines them using fixed weights totalling 1. It is not an Isolation Forest, trained anomaly detector, confidence score, or probability. The weights and ranges have not been calibrated against real construction outcomes.

This rule-based design is intentional: fitting an Isolation Forest to synthetic samples creates no evidence of real-world anomaly detection and adds substantial runtime dependencies without strengthening the project's primary schedule-decision demonstration.

## 3. Production evolution

A real pilot should use approved historic project snapshots and schedules. Calibrate any scoring thresholds with domain experts, evaluate against held-out time periods, compare against a simple baseline, and report false-positive/false-negative behaviour before presenting any model as validated. Preserve feature provenance, thresholds, model/version metadata and human review records.
