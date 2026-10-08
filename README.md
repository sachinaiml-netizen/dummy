# Real Estate Project Risk Intelligence

A domain-focused AI/ML prototype for detecting early signals of schedule and operational risk in real-estate projects.

## Problem

Construction teams typically track progress, cost, vendor performance, quality issues and open tasks in separate workflows. A useful intelligence layer should combine those signals and surface projects that need attention **before** a milestone is missed.

## Solution

This project exposes a REST API that converts project telemetry into:

- risk score (0–100)
- risk band (LOW / MEDIUM / HIGH)
- anomaly score
- leading indicators
- recommended next action

The included dataset is synthetic. No private company data is used.

## Architecture

```text
Project telemetry
(progress, cost, vendors, issues, defects)
                |
                v
        Pydantic validation
                |
                v
      Feature engineering
                |
        +-------+-------+
        |               |
        v               v
 Rule-based risk   Isolation Forest
 indicators        anomaly detection
        |               |
        +-------+-------+
                |
                v
        Explainable Risk Score
                |
                v
      FastAPI /risk endpoint
```

## Risk signals

- schedule variance
- cost variance
- vendor delay
- unresolved issues
- quality/inspection defects

The system deliberately combines an interpretable risk model with an unsupervised anomaly detector rather than presenting a single opaque model score.

## Example request

```json
{
  "project_id": "BRG-TOWER-07",
  "planned_progress": 72,
  "actual_progress": 58,
  "budget_variance_pct": 8.5,
  "vendor_delay_days": 9,
  "open_issues": 14,
  "quality_defects": 6
}
```

Example response:

```json
{
  "project_id": "BRG-TOWER-07",
  "risk_score": 87.4,
  "risk_band": "HIGH",
  "anomaly_score": 0.84,
  "leading_indicators": [
    "14 percentage-point schedule gap",
    "Vendor delay exceeds one week",
    "Budget variance above 5%"
  ],
  "recommended_action": "Escalate schedule recovery plan and review delayed vendor dependency."
}
```

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Tests

```bash
pytest -q
```

## Technical extensions

- time-series forecasting from milestone history
- image-based construction quality checks
- document/RAG layer for contracts and work orders
- PostgreSQL event store
- role-based alert routing
- project-level dashboard
- model monitoring and drift detection
