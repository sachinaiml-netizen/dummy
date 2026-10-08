# Architecture Notes

The prototype is intentionally split into two signals.

## 1. Interpretable risk score

Schedule, cost, vendor, issue and quality indicators contribute known weights to an initial risk score.

This makes the system easy to reason about with business stakeholders.

## 2. Anomaly detection

An Isolation Forest is fit on synthetic normal-project telemetry and provides a second signal for unusual combinations of project metrics.

The anomaly signal is only used as a bounded adjustment; it is not presented as a ground-truth probability.

## Production evolution

A production deployment would use time-series project history rather than a one-row snapshot, validate the model against historical project outcomes, version features and thresholds, and add monitoring for drift and false-positive/false-negative rates.
