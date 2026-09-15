from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.contact_workflow import ContactOutreachMethod, InvestigationStatus, OutreachOutcome


class InvestigationWrite(BaseModel):
    investigation_status: InvestigationStatus = InvestigationStatus.UNDER_RESEARCH
    designation_verified: bool | None = None
    department_verified: bool | None = None
    seniority_verified: bool | None = None
    email_verified: bool | None = None
    phone_verified: bool | None = None
    linkedin_verified: bool | None = None
    still_employed: bool | None = None
    relevant_to_warehouse_decisions: bool | None = None
    potential_decision_maker: bool | None = None
    research_notes: str | None = None


class InvestigationResponse(InvestigationWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    contact_id: int
    investigated_by_user_id: int | None
    selected_for_outreach: bool
    created_at: datetime
    updated_at: datetime


class OutreachWrite(BaseModel):
    method: ContactOutreachMethod
    performed_at: datetime
    purpose: str | None = Field(None, max_length=255)
    summary: str | None = None
    outcome: OutreachOutcome | None = None
    response_status: str | None = Field(None, max_length=50)
    next_action: str | None = None
    next_follow_up_at: datetime | None = None
    notes: str | None = None


class OutreachResponse(OutreachWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    contact_id: int
    performed_by_user_id: int
    created_at: datetime
    updated_at: datetime


class OutreachUpdate(BaseModel):
    method: ContactOutreachMethod | None = None
    performed_at: datetime | None = None
    purpose: str | None = Field(None, max_length=255)
    summary: str | None = None
    outcome: OutreachOutcome | None = None
    response_status: str | None = Field(None, max_length=50)
    next_action: str | None = None
    next_follow_up_at: datetime | None = None
    notes: str | None = None


class PipelineContext(BaseModel):
    active_pipeline_exists: bool
    active_lead_ids: list[int] = []
    active_requirement_ids: list[int] = []
    active_deal_ids: list[int] = []
    recommendation: str
    human_review_required: bool = True