# Architecture Notes

## 1. Primary decision engine

The primary Project Impact Lab engine is deterministic schedule logic. It calculates a baseline dependency network, injects a scenario delay, recomputes the finish date, and evaluates explicitly parameterized recovery actions. It is not an ML forecast.

## 2. Legacy snapshot-risk endpoint

The separate `POST /risk` endpoint returns a weighted score from schedule gap, budget variance, vendor delay, unresolved issues and quality defects. A bounded rule-based deviation index is retained under the legacy response key `anomaly_score` for compatibility.

The deviation index normalizes each signal against an illustrative reference range, caps each value at 1, and combines them using fixed weights totalling 1. It is not an Isolation Forest, trained anomaly detector, confidence score, or probability. The weights and ranges have not been calibrated against real construction outcomes.

This rule-based design is intentional: fitting an Isolation Forest to synthetic samples creates no evidence of real-world anomaly detection and adds substantial runtime dependencies without strengthening the project's primary schedule-decision demonstration.

## 3. Production evolution

A real pilot should use approved historic project snapshots and schedules. Calibrate any scoring thresholds with domain experts, evaluate against held-out time periods, compare against a simple baseline, and report false-positive/false-negative behaviour before presenting any model as validated. Preserve feature provenance, thresholds, model/version metadata and human review records.
