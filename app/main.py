from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .decision_engine import get_catalog, simulate_project
from .risk import assess_risk
from .schemas import ProjectTelemetry, RiskResponse, ScenarioRequest

app = FastAPI(
    title="Project Impact Lab",
    version="2.0.0",
    description=(
        "A synthetic-data proof of concept for critical-path-aware scenario analysis "
        "and explainable construction recovery decisions."
    ),
)

FRONTEND_FILE = Path(__file__).resolve().parent.parent / "static" / "index.html"


@app.get("/")
def home():
    if not FRONTEND_FILE.exists():
        raise HTTPException(status_code=404, detail="Frontend file is missing.")
    return FileResponse(FRONTEND_FILE)


@app.get("/health")
def health():
    return {"status": "ok", "product": "Project Impact Lab"}


@app.get("/api/catalog")
def catalog():
    return get_catalog()


@app.get("/api/scenario")
def default_scenario():
    return simulate_project()


@app.post("/api/scenario")
def scenario(request: ScenarioRequest):
    try:
        return simulate_project(
            disrupted_activity_id=request.disrupted_activity_id,
            delay_days=request.delay_days,
            exposure_lakh_per_day=request.exposure_lakh_per_day,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/risk", response_model=RiskResponse)
def risk(project: ProjectTelemetry) -> RiskResponse:
    result = assess_risk(project)
    return RiskResponse(project_id=project.project_id, **result)
