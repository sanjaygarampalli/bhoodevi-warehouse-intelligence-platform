from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.response_qualification import QualificationRecommendation, QualificationStatus
from app.models.company_intelligence import ContactDepartment, ContactSeniority, ContactMethodType, VerificationStatus


class QualificationWrite(BaseModel):
    status: QualificationStatus = QualificationStatus.DRAFT
    observed_facts: list[dict] = Field(default_factory=list)
    commercial_inference: str | None = None
    recommendation: QualificationRecommendation = QualificationRecommendation.CONTINUE_RESEARCH
    uncertainty: list[str] = Field(default_factory=list)
    warehouse_details: dict = Field(default_factory=dict)


class QualificationResponse(QualificationWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    contact_id: int
    outreach_activity_id: int
    reviewer_user_id: int | None
    human_review_required: bool
    created_at: datetime
    updated_at: datetime


class CompanyResolutionRequest(BaseModel):
    organization_id: int = Field(gt=0)
    company_name: str = Field(min_length=1, max_length=255)
    website: str | None = Field(default=None, max_length=255)


class ContactResolutionRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=255)
    email: str | None = None
    linkedin: str | None = None
    department: ContactDepartment = ContactDepartment.OTHER
    seniority: ContactSeniority = ContactSeniority.UNKNOWN
    method_verification: VerificationStatus = VerificationStatus.UNVERIFIED


class ResolutionResponse(BaseModel):
    result: str
    human_review_required: bool
    recommended_action: str
    company_id: int | None = None
    contact_id: int | None = None
    possible_company_ids: list[int] = Field(default_factory=list)
    possible_contact_ids: list[int] = Field(default_factory=list)


class CommercialContextResponse(BaseModel):
    company_id: int
    active_lead_ids: list[int]
    active_requirement_ids: list[int]
    active_deal_ids: list[int]
    qualification_ids: list[int]
    context: str
    recommended_next_action: str
    human_review_required: bool = True


class ExplicitLeadProgression(BaseModel):
    lead_number: str = Field(min_length=1, max_length=30)