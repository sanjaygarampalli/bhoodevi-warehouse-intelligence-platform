from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.warehouse_pilot import PilotAssessmentRequest


class WarehousePilotAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    organization_id: int
    company_id: int
    warehouse_id: int
    assessed_by_user_id: int
    capability_profile_id: int | None
    company_requirement_profile_id: int | None
    operational_profile_id: int | None
    commercial_profile_id: int | None
    requirement_assessment_id: int | None
    evaluation_version: str
    overall_classification: str
    result_snapshot: dict[str, Any]
    source_snapshot: dict[str, Any]
    assessed_at: datetime
    created_at: datetime


class WarehousePilotAssessmentCreateRequest(PilotAssessmentRequest):
    """Only source identifiers are accepted; result fields are evaluator-owned."""


class WarehousePilotAssessmentResult(BaseModel):
    assessment: WarehousePilotAssessmentResponse
    created: bool = True