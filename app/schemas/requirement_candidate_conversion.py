from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.lead import LeadPriority, MoveInTimeframe
from app.models.requirement import RequirementStatus, WarehouseType
from app.schemas.company import CompanyResponse
from app.schemas.lead import LeadResponse
from app.schemas.requirement import RequirementResponse


class RequirementCandidateConversionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    lead_number: str = Field(min_length=1, max_length=30)
    owner_user_id: int | None = Field(default=None, gt=0)
    priority: LeadPriority = LeadPriority.MEDIUM
    space_needed_sqft: Decimal | None = None
    requirement_type: str | None = Field(default=None, max_length=30)
    expected_monthly_rent: Decimal | None = None
    currency: str = Field("INR", pattern=r"^[A-Z]{3}$")
    move_in_timeframe: MoveInTimeframe | None = None
    lease_tenure_years: int | None = Field(default=None, gt=0)
    requirement_title: str | None = Field(default=None, min_length=1, max_length=255)
    requirement_description: str | None = None
    required_builtup_area: float | None = None
    minimum_area: float | None = None
    maximum_area: float | None = None
    warehouse_type: WarehouseType | None = None
    lease_duration_months: int | None = Field(default=None, gt=0)
    requirement_status: RequirementStatus = RequirementStatus.DRAFT


class RequirementCandidateConversionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    requirement_candidate_id: int
    company_id: int
    lead_id: int | None
    requirement_id: int | None
    status: str
    created_by_user_id: int
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    converted_at: datetime | None


class RequirementCandidateConversionResult(BaseModel):
    conversion: RequirementCandidateConversionResponse
    company: CompanyResponse
    lead: LeadResponse
    requirement: RequirementResponse
    created: bool