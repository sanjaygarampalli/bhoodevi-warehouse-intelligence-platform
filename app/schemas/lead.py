from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.lead import (
    LeadPriority,
    LeadSource,
    LeadStatus,
    MoveInTimeframe,
)


class LeadCreate(BaseModel):
    lead_number: str = Field(min_length=1, max_length=30)
    company_id: int
    status: LeadStatus = LeadStatus.NEW
    lead_source: LeadSource = LeadSource.MANUAL
    space_needed_sqft: Decimal | None = None
    requirement_type: str | None = Field(default=None, max_length=30)
    target_industry: str | None = Field(default=None, max_length=100)
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_state: str | None = Field(default=None, max_length=100)
    preferred_country: str | None = Field(default=None, max_length=100)
    expected_monthly_rent: Decimal | None = None
    currency: str | None = Field(default="INR", max_length=3)
    move_in_timeframe: MoveInTimeframe | None = None
    lease_tenure_years: int | None = None
    owner_user_id: int | None = None
    primary_decision_maker_id: int | None = None
    ai_score: Decimal | None = None
    priority: LeadPriority = LeadPriority.MEDIUM
    last_activity_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    disqualified_reason: str | None = Field(default=None, max_length=150)
    closed_reason: str | None = Field(default=None, max_length=150)


class LeadUpdate(BaseModel):
    lead_number: str | None = Field(default=None, min_length=1, max_length=30)
    company_id: int | None = None
    status: LeadStatus | None = None
    lead_source: LeadSource | None = None
    space_needed_sqft: Decimal | None = None
    requirement_type: str | None = Field(default=None, max_length=30)
    target_industry: str | None = Field(default=None, max_length=100)
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_state: str | None = Field(default=None, max_length=100)
    preferred_country: str | None = Field(default=None, max_length=100)
    expected_monthly_rent: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    move_in_timeframe: MoveInTimeframe | None = None
    lease_tenure_years: int | None = None
    owner_user_id: int | None = None
    primary_decision_maker_id: int | None = None
    ai_score: Decimal | None = None
    priority: LeadPriority | None = None
    last_activity_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    disqualified_reason: str | None = Field(default=None, max_length=150)
    closed_reason: str | None = Field(default=None, max_length=150)


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_number: str
    company_id: int
    status: LeadStatus
    lead_source: LeadSource
    space_needed_sqft: Decimal | None
    requirement_type: str | None
    target_industry: str | None
    preferred_city: str | None
    preferred_state: str | None
    preferred_country: str | None
    expected_monthly_rent: Decimal | None
    currency: str | None
    move_in_timeframe: MoveInTimeframe | None
    lease_tenure_years: int | None
    owner_user_id: int | None
    primary_decision_maker_id: int | None
    ai_score: Decimal | None
    priority: LeadPriority
    last_activity_at: datetime | None
    next_follow_up_at: datetime | None
    disqualified_reason: str | None
    closed_reason: str | None
    created_at: datetime
    updated_at: datetime