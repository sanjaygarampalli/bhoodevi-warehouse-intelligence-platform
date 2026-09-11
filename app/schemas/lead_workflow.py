"""Schemas for the lead qualification and opportunity creation workflow."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class QualifyLeadRequest(BaseModel):
    """Request schema for qualifying a lead.

    The workflow validates prerequisites (company, decision makers, active
    requirement) and transitions the lead to QUALIFIED status.
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class QualifyLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_number: str
    status: str
    company_id: int
    previous_status: str
    disqualified_reason: str | None = None


class LeadTransitionRequest(BaseModel):
    """Transition a lead to a new status with an optional reason.

    The workflow validates that the requested transition is legal
    according to the lead lifecycle state machine.
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    new_status: str = Field(min_length=1, max_length=20,
        description="Target lead status (e.g. DISCOVERED, CONTACTED, NEGOTIATING, DORMANT)")
    reason: str | None = Field(None, max_length=150,
        description="Optional reason for the transition")


class LeadTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_number: str
    status: str
    company_id: int
    previous_status: str
    transition_reason: str | None = None


class CreateOpportunityRequest(BaseModel):
    """Create a Deal (opportunity) from a qualified lead context.

    The workflow picks the best active requirement and best eligible
    warehouse match automatically. The caller may optionally override the
    requirement selection by supplying ``requirement_id``.
    """
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    deal_name: str = Field(min_length=1, max_length=255)
    stage_id: int = Field(gt=0)
    requirement_id: int | None = Field(None, gt=0,
        description="Optional explicit requirement override")
    expected_revenue: Decimal | None = Field(None, ge=0, max_digits=16, decimal_places=2)
    currency: str = Field("INR", pattern=r"^[A-Z]{3}$")
    expected_close_date: date | None = None
    notes: str | None = None


class CreateOpportunityResponse(BaseModel):
    """Result of opportunity creation: the new deal and context summary."""
    deal_id: int
    deal_name: str
    lead_id: int
    requirement_id: int
    selected_warehouse_match_id: int | None
    organization_id: int
    stage_id: int
    deal_status: str
    lead_status: str
    initial_task_id: int | None
    created_at: datetime


class DisqualifyLeadRequest(BaseModel):
    """Request body for disqualifying a lead with a reason."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    reason: str = Field(min_length=1, max_length=150)


class SeedPipelineRequest(BaseModel):
    """Auto-create default pipeline stages for an organization."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    organization_id: int = Field(gt=0)


class SeedPipelineResponse(BaseModel):
    stages_created: int
    stages_present: int
    organization_id: int