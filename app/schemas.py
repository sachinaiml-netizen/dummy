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


class RiskFeatureContribution(BaseModel):
    feature: str
    label: str
    raw_value: float
    standardized_value: float
    logit_contribution: float
    direction: str


class RiskProofMetrics(BaseModel):
    test_rows: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    brier_score: float
    majority_baseline_accuracy: float


class RiskProofResponse(BaseModel):
    project_id: str
    model_version: str
    model_type: str
    training_data_kind: str
    training_rows: int
    score_pct: float
    risk_band: str
    score_semantics: str
    target_column: str
    target_definition: str
    top_drivers: list[RiskFeatureContribution]
    feature_contributions: list[RiskFeatureContribution]
    test_metrics: RiskProofMetrics
    evaluation_scope: str
    important_warning: str
