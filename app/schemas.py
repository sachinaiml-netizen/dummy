from typing import Literal

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


class DelayRiskRequest(BaseModel):
    """Input for the experimental delay-risk model and later labelled-data retraining."""
    project_id: str = Field(min_length=1, max_length=80)
    planned_progress: float = Field(ge=0, le=100)
    actual_progress: float = Field(ge=0, le=100)
    budget_variance_pct: float = Field(ge=-100, le=500)
    vendor_delay_days: int = Field(ge=0, le=365)
    open_issues: int = Field(ge=0, le=10000)
    quality_defects: int = Field(ge=0, le=10000)
    total_float_days: int | None = Field(default=None, ge=-365, le=365)
    float_consumed_pct: float | None = Field(default=None, ge=0, le=1000)
    procurement_delay_days: int | None = Field(default=None, ge=0, le=365)
    long_lead_items_at_risk: int | None = Field(default=None, ge=0, le=500)
    approval_overdue_days: int | None = Field(default=None, ge=0, le=365)
    labour_shortage_pct: float | None = Field(default=None, ge=0, le=100)
    weather_lost_days_30d: int | None = Field(default=None, ge=0, le=90)
    design_changes_30d: int | None = Field(default=None, ge=0, le=365)
    safety_actions_overdue: int | None = Field(default=None, ge=0, le=1000)
    phase: Literal["design", "structure", "envelope", "finishes", "commissioning"] | None = None


class DelayRiskResponse(BaseModel):
    project_id: str
    model_name: str
    model_version: str
    model_stage: str
    target: str
    target_definition: str
    score_available: bool
    synthetic_model_probability_pct: float | None
    risk_band: str | None
    risk_band_thresholds: dict[str, float]
    data_completeness_pct: float
    missing_optional_fields: list[str]
    out_of_training_range_fields: list[str]
    reliability_status: str
    top_model_contributors: list[dict[str, str | float]]
    evaluation_scope: str
    dataset_rows: int
    split_rows: dict[str, int]
    split_project_counts: dict[str, int]
    test_metrics: dict[str, str | int | float]
    model_limitations: list[str]
    interpretation_warning: str
