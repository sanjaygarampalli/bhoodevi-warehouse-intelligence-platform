from pydantic import BaseModel, Field


class WarehouseEvaluationRequest(BaseModel):
    warehouse_id: int = Field(gt=0)
    company_id: int = Field(gt=0)


class FactorResult(BaseModel):
    factor: str
    requirement: object
    warehouse_value: object
    priority: str
    status: str
    score_impact: int
    explanation: str


class WarehouseEvaluationResponse(BaseModel):
    warehouse_id: int
    company_id: int
    current_match_score: int = Field(ge=0, le=100)
    classification: str
    mandatory_gap: bool
    missing_mandatory_requirements: list[str]
    planned_capabilities: list[str]
    factor_results: list[FactorResult]
    explanation: str