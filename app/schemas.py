from pydantic import BaseModel, Field


class ProjectTelemetry(BaseModel):
    project_id: str = Field(min_length=1, max_length=80)
    planned_progress: float = Field(ge=0, le=100)
    actual_progress: float = Field(ge=0, le=100)
    budget_variance_pct: float = Field(ge=-100, le=500)
    vendor_delay_days: int = Field(ge=0, le=365)
    open_issues: int = Field(ge=0, le=10000)
    quality_defects: int = Field(ge=0, le=10000)


class RiskResponse(BaseModel):
    project_id: str
    risk_score: float
    risk_band: str
    anomaly_score: float
    leading_indicators: list[str]
    recommended_action: str


class ScenarioRequest(BaseModel):
    disrupted_activity_id: str = Field(default="PR-01", min_length=1, max_length=20)
    delay_days: int = Field(default=14, ge=0, le=60)
    exposure_lakh_per_day: float = Field(default=4.5, ge=0, le=100)


class CsvScheduleRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=250000)
    disrupted_task_id: str | None = Field(default=None, max_length=80)
    delay_days: int = Field(default=0, ge=0, le=60)
