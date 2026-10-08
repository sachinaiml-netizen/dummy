from fastapi import FastAPI

from .risk import assess_risk
from .schemas import ProjectTelemetry, RiskResponse

app = FastAPI(
    title="Real Estate Project Risk Intelligence",
    version="1.0.0",
    description="Explainable project-risk assessment using synthetic telemetry.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/risk", response_model=RiskResponse)
def risk(project: ProjectTelemetry) -> RiskResponse:
    result = assess_risk(project)
    return RiskResponse(project_id=project.project_id, **result)
