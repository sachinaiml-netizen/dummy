# Synthetic-Trained Delay-Risk Model — Model Card

**Version:** 0.1.0  
**Stage:** Research prototype  
**Training method:** StandardScaler + LogisticRegression; training dependency only  
**Inference:** Pure Python; no scikit-learn runtime dependency  
**Training snapshot count:** 50,000 generated rows  
**Target:** material_delay_next_60d

## What it predicts

The output is a model score for the generated target: whether a project snapshot will experience a material handover delay of more than seven days over the next 60 days. Labels in the current dataset are simulated from an explicit probabilistic mechanism. They are not observed outcomes from Prestige, other contractors, or public project records.

Synthetic examples contain progress gap, budget variance, vendor/procurement delays, issue and defect counts, total float, float consumption, long-lead exposure, approval age, labour shortage, weather disruption, design changes, overdue safety actions, and project phase. The generator introduces correlations between signals and hidden synthetic execution-friction/complexity factors, phase interactions and label noise. Its purpose is to exercise the training, evaluation and inference pipeline, not to claim that these weights represent construction reality.

## Training and holdout design

The default seed is 20261010. 50,000 generated rows are split by project ID into 35,000 training rows, 7,500 validation rows, and 7,500 untouched test rows. The validation set is used for evaluation/diagnostics, not model fitting. The synthetic generator assigns a distinct synthetic project ID to each row; the split is still only independent with respect to this generator, not independent evidence from real projects.

| Untouched synthetic test metric | Result |
|---|---:|
| ROC-AUC | 0.8227 |
| Average precision | 0.7250 |
| Brier score | 0.1598 |
| Brier skill vs. prevalence-only baseline | 0.3005 |
| Accuracy at 0.50 threshold | 0.7648 |
| Precision at 0.50 threshold | 0.7051 |
| Recall at 0.50 threshold | 0.5742 |
| Positive-label share in test set | 0.3532 |

These figures describe synthetic holdout performance only. ROC-AUC measures ranking, not calibration. The Brier score is better than the prevalence-only baseline under this generator, but that does not establish calibration on actual construction data. The LOW/MEDIUM/HIGH cutoffs in this demo are illustrative thresholds, not Prestige policy.

## How to reproduce training

Install development dependencies, then run from the repository root:

    python tools/train_synthetic_risk_model.py --samples 50000 --seed 20261010 --output app/models/synthetic_delay_risk_v1.json

To also create the complete generated dataset locally:

    python tools/train_synthetic_risk_model.py --samples 50000 --seed 20261010 --dataset-csv /tmp/project-impact-lab-synthetic-50k.csv

The script can also train from an approved labelled CSV. Required fields are project_id, snapshot_date, planned_progress, actual_progress, budget_variance_pct, vendor_delay_days, open_issues, quality_defects, total_float_days, float_consumed_pct, procurement_delay_days, long_lead_items_at_risk, approval_overdue_days, labour_shortage_pct, weather_lost_days_30d, design_changes_30d, safety_actions_overdue, phase, plus a binary material_delay_next_60d column. The target must mean exactly “handover was more than seven days late in the 60 days after this snapshot date”. Each snapshot may contain only information available at that date. The script validates basic ranges, ISO dates and unique project/date pairs, and keeps every snapshot for a project in a single split to reduce project-level leakage. Minimum: 200 rows, 20 distinct projects and 20 examples of each outcome; this is only a technical minimum. A real pilot should normally aim for substantially more projects and time periods.

Use only approved, appropriately anonymised data. Training is performed from local files and the script does not upload data. Do not commit confidential raw records or a real-data-trained artifact to a public repository without explicit authorization and review.

## Prediction API and input guards

- GET /api/risk/model-info returns model provenance and the synthetic/labelled-data holdout metrics.
- POST /api/risk/predict scores a project snapshot and reports the model stage, input completeness, unsupported input ranges, top additive model associations and limitations.
- A score is withheld when fewer than 75% of expected fields are present or any supplied numeric field falls outside the supported training range. Missing optional fields use illustrative defaults for feature construction, but the response does not pretend a score is reliable when there is insufficient input coverage.
- The older POST /risk heuristic endpoint is retained for backwards compatibility. It is not the trained model.

## Safety and limitations

1. **No real-world validity established.** Synthetic-only training cannot prove this will work on Prestige data. Synthetic “probabilities” are not calibrated real-world probabilities.
2. **No causal claim.** Additive contributors describe the fitted model, not the effect of changing one construction factor.
3. **Simplified inputs.** The model does not consume native Primavera P6 files, calendars, resource-loaded schedules, contract terms, site logs or live Autodesk/Primavera data.
4. **Data coverage matters.** Missing, stale, inconsistent or differently defined status fields can make a score meaningless. A future real-data model must enforce field definitions, time stamps, units and provenance.
5. **Human review only.** No automated stop-work, safety, contract, payment or recovery decision should be triggered by this prototype.

## Path to a defensible real-data pilot

Obtain authorised and time-indexed historical snapshots with confirmed future outcomes; define the target with project-controls specialists; split evaluation by project and time; compare against simple baselines; assess recall, precision, calibration/Brier score and performance by phase/project type; document false negatives and false positives; check drift and missing-data patterns; choose thresholds with the project team; and require human sign-off. Do not rely on a random synthetic holdout as a substitute.

## External basis

- U.S. GAO, [Schedule Assessment Guide (GAO-16-89G)](https://www.gao.gov/products/gao-16-89g): critical/near-critical path assessment, reasonable float, schedule logic and updated status are central to credible schedule analysis.
- Amoatey and colleagues, [Machine learning model for delay risk assessment in tall building projects](https://www.tandfonline.com/doi/full/10.1080/15623599.2020.1768326): illustrates using domain delay factors and expert-collected project-risk input for ML. It does not provide transferable evidence that this synthetic model predicts Prestige project outcomes.
- scikit-learn, [Probability calibration](https://scikit-learn.org/stable/modules/calibration.html): emphasizes evaluating probability calibration independently of discrimination.
