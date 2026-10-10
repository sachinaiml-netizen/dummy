# Risk Model Training and Real-Data Validation

## Current model status

The shipped artifact app/risk_model.json is synthetic-logistic-v1. It uses 60,000 generated snapshots (42,000 train, 9,000 validation, 9,000 held-out test). Its score is a synthetic-model score, not a calibrated real-world probability. Metrics measure how the classifier recovers an invented generator's label.

The route POST /api/risk/proof-model takes the current telemetry schema and evaluates a snapshot. It is a demonstrator; do not use it to approve, reject, price, staff or escalate a real project based on the score alone.

## Option A: reproduce the synthetic pipeline

The command used by CI to rebuild and check the artifact is:

    python scripts/train_risk_model.py --rows 60000 --seed 20261010 --model-version synthetic-logistic-v1 --max-epochs 240 --output /tmp/risk-model-rebuilt.json

To create a smaller quick experiment:

    python scripts/train_risk_model.py --rows 3000 --seed 42 --max-epochs 30 --output /tmp/risk-model-smoke.json

Changing seed, row count or model parameters creates a different experiment; do not compare its results as if they were the same test set. More synthetic rows can reduce simulation noise, but they do not add observed construction truth.

## Option B: evaluate approved historical snapshots with known outcomes

This mode trains a candidate model from labelled historical snapshots. It will not invent labels from current telemetry and will not overwrite the active app/risk_model.json artifact.

### Required CSV schema

    project_id,snapshot_date,planned_progress,actual_progress,budget_variance_pct,vendor_delay_days,open_issues,quality_defects,target_high_risk_30d

Rules:
- One row is one project snapshot at a known reporting date.
- snapshot_date is ISO YYYY-MM-DD.
- Each project_id + snapshot_date pair must be unique.
- The six numeric fields must be known as of that snapshot. Do not include facts that occurred after that date.
- target_high_risk_30d must be 0 or 1, based on a previously agreed and verifiable event observed within the following 30 days. The project-controls owner must define precisely what “high risk” means before modelling; the script does not derive a true target from the six inputs.
- Use only records and fields the data owner has explicitly authorised for this purpose.

### Train the separate candidate artifact

    python scripts/train_risk_model.py --input-csv approved_labeled_snapshots.csv --model-version pilot-candidate-01 --output /tmp/risk-model-candidate.json

By default, the script applies a chronological 70/15/15 date split with a 30-day embargo before validation and test periods. It records how many rows were excluded around the split boundaries. Every partition must have both labels, at least 30 rows, and the CSV must have at least 12 distinct snapshot dates. Small or narrow datasets may correctly fail those requirements; do not remove safeguards solely to force a training run.

The candidate file is a research artifact. It is not automatically loaded by the public app. The trainer refuses to overwrite the active proof-model artifact when --input-csv is used; the candidate must be reviewed and promoted deliberately through a separate change.

### What this split does—and does not—prove

The chronological split asks how the model performs on later dates in a portfolio where some projects may also have earlier training snapshots. The 30-day embargo is designed to reduce overlap between snapshots and the future-outcome window around partition boundaries. It does not prove performance on entirely unseen projects. Before a real pilot, add a project-held-out assessment as a separate evaluation.

### Review the candidate

At a minimum, review:
- accuracy versus the majority-class baseline;
- precision, recall, F1 and confusion matrix (which show false positives and missed positives at the current 0.5 threshold);
- ROC-AUC and Brier score;
- event prevalence in each temporal partition;
- outcome-definition consistency, missingness and duplicate snapshots;
- whether the model adds value over the existing rule-based baseline;
- error examples reviewed with project controls, and results for relevant project/phase groups.

These metrics are not enough by themselves. Calibration, class-specific errors, subgroup behavior and operational alert thresholds require review. No candidate trained on historical records is automatically safe or calibrated for live decisions.

## Protect company data

Do not upload actual Prestige schedules, cost reports, internal project records or confidential data into this public repository or commit them to a public Git branch. Run the training command only in an approved environment under the data owner's access rules. Store historical input CSVs and candidate model files in an approved location. This prototype has not been approved for production data processing, and local candidate training is not an integration with Prestige systems.

## Suggested real-pilot gate

1. Define one observable target and horizon with project controls.
2. Check that snapshot features are available before the target event.
3. Train a candidate using approved historical snapshots.
4. Review time-separated and project-held-out results, calibration and errors.
5. Run a human-reviewed shadow period without letting the score automatically trigger actions.
6. Compare with the existing planning process and simple baselines; do not deploy if it fails agreed criteria.
7. Version any promoted artifact and preserve rollback, monitoring and human sign-off.

The schedule/finish-date engine remains deterministic CPM. This risk classifier is separate and experimental.
