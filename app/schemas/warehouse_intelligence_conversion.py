from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.deal import DealResponse


class WarehouseMatchOpportunityConversionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    deal_name: str = Field(min_length=1, max_length=255)
    requirement_id: int = Field(gt=0)
    stage_id: int = Field(gt=0)
    expected_revenue: Decimal | None = Field(None, ge=0, max_digits=16, decimal_places=2)
    currency: str = Field("INR", pattern=r"^[A-Z]{3}$")
    expected_close_date: date | None = None
    notes: str | None = None


class WarehouseIntelligenceConversionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: int
    organization_id: int
    source_type: Literal["WAREHOUSE_MATCH"]
    warehouse_match_id: int
    deal_id: int | None
    status: str
    created_by_user_id: int
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    converted_at: datetime | None


class WarehouseMatchOpportunityConversionResponse(BaseModel):
    conversion: WarehouseIntelligenceConversionResponse
    deal: DealResponse
    created: bool