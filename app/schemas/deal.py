from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.deal_pipeline_stage import DealPipelineStageResponse
from app.models.deal import LostReasonCategory


class DealCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    deal_name: str = Field(min_length=1, max_length=255)
    lead_id: int = Field(gt=0)
    requirement_id: int = Field(gt=0)
    stage_id: int = Field(gt=0)
    selected_warehouse_match_id: int | None = Field(None, gt=0)
    expected_revenue: Decimal | None = Field(None, ge=0, max_digits=16, decimal_places=2)
    currency: str = Field("INR", pattern=r"^[A-Z]{3}$")
    expected_close_date: date | None = None
    notes: str | None = None


class DealUpdate(BaseModel):
    """Opportunity identity and stage cannot be edited through generic updates."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    deal_name: str | None = Field(None, min_length=1, max_length=255)
    selected_warehouse_match_id: int | None = Field(None, gt=0)
    expected_revenue: Decimal | None = Field(None, ge=0, max_digits=16, decimal_places=2)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    expected_close_date: date | None = None
    notes: str | None = None

    @field_validator("deal_name", "currency")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class DealTransition(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    to_stage_id: int = Field(gt=0)
    change_reason: str | None = Field(None, max_length=255)
    lost_reason_category: LostReasonCategory | None = None
    final_commercial_amount: Decimal | None = Field(None, ge=0, max_digits=16, decimal_places=2)
    final_commercial_currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    final_lease_duration_months: int | None = Field(None, gt=0)
    outcome_notes: str | None = Field(None, max_length=5000)
    closure_evidence_reference: str | None = Field(None, max_length=255)


class DealResponse(DealCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    stage: DealPipelineStageResponse
    stage_entered_at: datetime
    deal_status: Literal["OPEN", "WON", "LOST"]
    closed_at: datetime | None
    closed_reason: str | None
    lost_reason_category: LostReasonCategory | None
    final_commercial_amount: Decimal | None
    final_commercial_currency: str | None
    final_lease_duration_months: int | None
    outcome_notes: str | None
    closure_evidence_reference: str | None
    created_at: datetime
    updated_at: datetime


class DealStageHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deal_id: int
    from_stage_id: int | None
    to_stage_id: int
    from_stage_key: str | None
    from_stage_name: str | None
    to_stage_key: str
    to_stage_name: str
    changed_by_user_id: int | None
    changed_at: datetime
    change_reason: str | None