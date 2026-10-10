# Real-data risk-model validation playbook

Status: experimental training path. The active dashboard model remains `0.1.0-synthetic` until an approved promotion process exists.

## What is trained today

`scripts/train_synthetic_risk_model.py` fits a standardized logistic-regression baseline on 115,000 generated rows: 70,000 training, 15,000 validation, 15,000 same-generator holdout and 15,000 shifted synthetic stress cases. On the same-generator holdout, ROC-AUC was 0.800, Brier score 0.141 and log loss 0.444. At the experimental 25% screening threshold, recall was 0.718 and precision was 0.480. In the shifted synthetic set, positive-label prevalence increased from 25.1% to 55.6% and log loss worsened from 0.444 to 0.492.

These numbers describe recovery of an invented synthetic label. They do **not** estimate performance on Prestige, real estate construction projects, or a real delay/overrun event. High recall at the illustrative screening threshold comes with many false alerts. The score must remain a research signal, not an operational probability.

Reproduce the committed model locally with:

```bash
python scripts/train_synthetic_risk_model.py --check
```

Optionally export the reproducible synthetic examples to a local file:

```bash
python scripts/train_synthetic_risk_model.py --export-dataset data/synthetic_risk_samples.csv
```

## Training a candidate from authorised historical data

The real-data candidate trainer does **not** create target labels. It requires a target reviewed by project controls and uses only telemetry fields recorded at the snapshot date. Each row must represent one project status snapshot, with a `target_high_risk_30d` value of `1` if the agreed event occurred within the following 30 days and `0` otherwise.

Required CSV header:

```csv
project_id,snapshot_date,planned_progress,actual_progress,budget_variance_pct,vendor_delay_days,open_issues,quality_defects,target_high_risk_30d
```

Rules:

- `snapshot_date` must use `YYYY-MM-DD` and identify when those features were known.
- `target_high_risk_30d` must be an **observed outcome**, not a threshold copied from the same input features. Decide the business meaning before preparing labels.
- Supply only snapshots whose complete 30-day outcome window is known. The trainer checks `--outcomes-observed-through`, but it cannot independently certify the truth of your labels.
- The input must contain at least 100 snapshots, 12 distinct snapshot dates and five distinct projects. The group holdout and both future test partitions must each have at least 30 rows and both outcome classes; otherwise training stops rather than reporting weak validation as success.
- Project IDs and snapshot dates are used for splitting only. They are not model features, and raw rows/project IDs are not copied into the candidate artifact.

Example command (replace the paths, event definition and date with your approved dataset's details):

```bash
python scripts/train_labeled_risk_candidate.py \
  --input-csv /path/to/approved-labelled-snapshots.csv \
  --target-definition "Critical handover slips by more than 14 days within 30 days of a status snapshot" \
  --outcomes-observed-through 2026-10-10 \
  --output artifacts/risk_model_candidate.json
```

Set `--outcomes-observed-through` to the latest date through which the full 30-day outcomes have actually been verified, not automatically to today's date. The output path is separate from the active synthetic artifact. The script refuses to overwrite `static/synthetic_risk_model.json` and refuses to replace an existing candidate unless `--overwrite-candidate` is explicitly passed.

### Split design

The candidate trainer runs two complementary future tests:

1. **Future temporal test:** projects represented in the development set, using later dates after a 30-day embargo.
2. **Future held-out-project test:** projects excluded entirely from training and validation, using the same later period.

Training and validation are separated chronologically with an embargo at each boundary. This helps reduce leakage from overlapping 30-day outcome windows and repeated snapshots. It still does not prove that the model generalizes to every developer, asset class, city, contract or delivery method. The candidate artifact includes metrics for both test groups, a constant-prevalence baseline, the chosen training/validation loss and split counts.

## How to interpret the candidate

The output is marked `CANDIDATE_REAL_LABELLED_NOT_ACTIVE`. It contains fitted coefficients, scaling values, split metadata and aggregate evaluation metrics; it does not contain raw per-project records or the project IDs assigned to the held-out groups. **The active API still serves the synthetic model.** Producing a candidate file does not change the deployed app or automatically promote a model.

Before any promotion, project controls and model reviewers should:

1. Confirm the label definition, observation window, and point-in-time correctness of every feature.
2. Compare the temporal and held-out-project metrics with a constant/base-rate and rule-based baseline.
3. Inspect false negatives, false alerts, precision/recall at proposed thresholds, Brier score, log loss and calibration—not accuracy alone.
4. Check performance by project type, construction phase, project size, region and reporting cadence where sample sizes permit; record uncertainty for small subgroups.
5. Run a historical backtest and then a human-reviewed shadow period. Record every model version, threshold, review and override.
6. Promote only through a deliberate, reviewed change that preserves rollback to the previous model. Do not use the model for automatic safety, contractual, payment, staffing or handover decisions.

For privacy and data control, run the trainer locally in an approved environment. Do not paste confidential Prestige schedules or project data into a chat or commit raw historical data to this public repository.

## Research basis

- NIST, *AI Risk Management Framework*: trustworthiness includes validity, reliability, transparency and evaluation through the lifecycle. https://www.nist.gov/itl/ai-risk-management-framework
- NIST, *Valid and Reliable*: deployment beyond the settings represented in development can reduce trustworthiness. https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/
- scikit-learn, *Cross-validation*: training and evaluation must use separate data; a held-out test is needed to assess unseen observations. https://scikit-learn.org/stable/modules/cross_validation.html
- Radhe Shyam and Sanjay Tiwari (2026), *Predictive Assessment of Construction Delays on Schedule, Cost, and Quality Performance Using Machine Learning and Multi-Criteria Decision Analysis*. This recent study is evidence that construction-delay modelling is an active applied research area, not validation of this prototype. https://doi.org/10.1007/s40030-026-00989-y

The next meaningful quality improvement after a first authorised dataset is not simply increasing row count. It is improving outcome definitions and point-in-time data quality, then reviewing errors and calibration on truly future and unseen-project records.
