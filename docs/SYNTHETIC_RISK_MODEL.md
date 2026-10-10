# Experimental Synthetic Risk Model v0.1.0

Status: experimental. Trained only on synthetic labels; not ready for live operational decisions.

The new supervised logistic-regression model is separate from Float-Burn Watch and the existing rule-based risk endpoint. The model is stored at static/synthetic_risk_model.json. Inference does not retrain the model during a request.

## Data volume

The reproducible generator creates 115,000 synthetic rows: 70,000 train; 15,000 validation; 15,000 same-generator test; and 15,000 shifted synthetic stress-test rows. The training seed is 20261010. The target is an authored simulated event, not a measured construction outcome.

Reproduce and check the committed model with: python scripts/train_synthetic_risk_model.py --check

Optionally export the complete synthetic dataset with: python scripts/train_synthetic_risk_model.py --export-dataset data/synthetic_risk_samples.csv

## Method and result

The model uses five inputs: non-negative planned-vs-actual progress gap, positive budget variance, vendor delay days, open issues, and quality defects. Features are standardised with training-set means and scales. Logistic regression is fitted by deterministic full-batch gradient descent with L2 regularisation using only the Python standard library.

Held-out synthetic test results: ROC AUC 0.800; Brier score 0.141; log loss 0.444. A constant base-rate baseline had Brier score 0.188 and log loss 0.564. At the 25% screening threshold, recall was 0.718 and precision was 0.480, so false alerts remain common.

The shift-stress dataset changed the synthetic positive rate from 25.1% to 55.6%; log loss worsened from 0.444 to 0.492 even though AUC increased. This is a reminder that discrimination is different from probability calibration. It is not a test on Prestige or any real developer.

## How to interpret the API

POST /risk-model returns a synthetic-label score, LOW/WATCH/HIGH band, leading model terms, training counts, holdout metrics and warnings. GET /risk-model/info returns the model card. The existing POST /risk endpoint remains the rule-based baseline.

The percentage is a probability of the synthetic label under the authored generator, not a calibrated probability of a real construction delay. Signals are statistical contributions, not causal explanations. Do not use the output to trigger safety, contractual, financial or construction decisions automatically.

## Real-data validation gate

For real use, first agree on an observable future outcome (for example, handover slip above a defined number of days within a fixed horizon). Build historical snapshots using only information available at each status date. Split evaluation by whole projects and later time periods to prevent leakage from repeated snapshots. Compare the model against simple baselines; report ROC/PR AUC, precision/recall, Brier score, log loss, calibration, subgroup errors and false-alert examples. Run retrospective backtests and a human-reviewed shadow period before any controlled pilot. Retraining must use validated real outcome labels, not unlabelled records alone.

## References

Scikit-learn, cross-validation: https://scikit-learn.org/stable/modules/cross_validation.html
NIST AI RMF Measure: https://airc.nist.gov/airmf-resources/playbook/measure/
U.S. GAO Schedule Assessment Guide: https://www.gao.gov/assets/gao-16-89g.pdf
Sari et al. (2026), machine-learning prediction of infrastructure estimate-at-completion using construction monitoring data: https://link.springer.com/article/10.1007/s42452-026-08965-8
