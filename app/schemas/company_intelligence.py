from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, TypeAdapter, model_validator

from app.models.company_intelligence import (
    ContactDepartment, ContactMethodType, ContactSeniority, EstimateConfidence,
    IcpClassification, NextBestActionType, OpportunityPriority, VerificationStatus,
    WarehouseDependency, WarehouseUseCase,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IntelligenceProfileWrite(StrictModel):
    industry: str | None = Field(None, max_length=150)
    sub_industry: str | None = Field(None, max_length=150)
    business_model: str | None = Field(None, max_length=50)
    employee_count_min: int | None = Field(None, ge=0)
    employee_count_max: int | None = Field(None, ge=0)
    annual_revenue_min: Decimal | None = Field(None, ge=0)
    annual_revenue_max: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    headquarters_city: str | None = Field(None, max_length=100)
    headquarters_state: str | None = Field(None, max_length=100)
    headquarters_country: str | None = Field(None, max_length=100)
    operational_geography: dict | None = None
    is_expanding: bool = False
    is_hiring: bool = False
    is_entering_new_market: bool = False
    is_raising_capacity: bool = False
    is_launching_new_product: bool = False
    is_opening_new_facility: bool = False
    indicator_evidence: dict | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.employee_count_min is not None and self.employee_count_max is not None and self.employee_count_min > self.employee_count_max:
            raise ValueError("employee_count_min must be <= employee_count_max")
        if self.annual_revenue_min is not None and self.annual_revenue_max is not None and self.annual_revenue_min > self.annual_revenue_max:
            raise ValueError("annual_revenue_min must be <= annual_revenue_max")
        return self


class IntelligenceProfileUpdate(IntelligenceProfileWrite):
    industry: str | None = Field(None, max_length=150)
    sub_industry: str | None = Field(None, max_length=150)
    business_model: str | None = Field(None, max_length=50)
    employee_count_min: int | None = Field(None, ge=0)
    employee_count_max: int | None = Field(None, ge=0)
    annual_revenue_min: Decimal | None = Field(None, ge=0)
    annual_revenue_max: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    is_expanding: bool | None = None
    is_hiring: bool | None = None
    is_entering_new_market: bool | None = None
    is_raising_capacity: bool | None = None
    is_launching_new_product: bool | None = None
    is_opening_new_facility: bool | None = None


class WarehouseProfileWrite(StrictModel):
    warehouse_dependency: WarehouseDependency = WarehouseDependency.UNKNOWN
    estimated_area_min_sqft: Decimal | None = Field(None, ge=0)
    estimated_area_max_sqft: Decimal | None = Field(None, ge=0)
    estimate_confidence: EstimateConfidence = EstimateConfidence.LOW
    warehouse_requirement_notes: str | None = None
    use_cases: list[WarehouseUseCase] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.estimated_area_min_sqft is not None and self.estimated_area_max_sqft is not None and self.estimated_area_min_sqft > self.estimated_area_max_sqft:
            raise ValueError("estimated_area_min_sqft must be <= estimated_area_max_sqft")
        return self


class WarehouseProfileUpdate(StrictModel):
    warehouse_dependency: WarehouseDependency | None = None
    estimated_area_min_sqft: Decimal | None = Field(None, ge=0)
    estimated_area_max_sqft: Decimal | None = Field(None, ge=0)
    estimate_confidence: EstimateConfidence | None = None
    warehouse_requirement_notes: str | None = None
    use_cases: list[WarehouseUseCase] | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.estimated_area_min_sqft is not None and self.estimated_area_max_sqft is not None and self.estimated_area_min_sqft > self.estimated_area_max_sqft:
            raise ValueError("estimated_area_min_sqft must be <= estimated_area_max_sqft")
        return self


class ContactWrite(StrictModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    full_name: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=255)
    department: ContactDepartment = ContactDepartment.OTHER
    seniority: ContactSeniority = ContactSeniority.UNKNOWN
    is_primary: bool = False

    @model_validator(mode="after")
    def name_present(self):
        if not self.full_name and not (self.first_name or self.last_name):
            raise ValueError("a full_name or first/last name is required")
        return self


class ContactUpdate(StrictModel):
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    full_name: str | None = Field(None, max_length=255)
    job_title: str | None = Field(None, max_length=255)
    department: ContactDepartment | None = None
    seniority: ContactSeniority | None = None
    is_primary: bool | None = None


class ContactMethodWrite(StrictModel):
    method_type: ContactMethodType
    value: str = Field(min_length=1, max_length=2048)
    is_primary: bool = False
    is_verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verification_source: str | None = Field(None, max_length=255)
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def validate_method(self):
        if self.is_verified and self.verification_status != VerificationStatus.VERIFIED:
            raise ValueError("is_verified requires VERIFIED verification_status")
        if self.verification_status == VerificationStatus.VERIFIED and not self.is_verified:
            raise ValueError("VERIFIED requires is_verified=true")
        if self.method_type == ContactMethodType.EMAIL:
            TypeAdapter(EmailStr).validate_python(self.value)
        if self.method_type in {ContactMethodType.LINKEDIN, ContactMethodType.WEBSITE}:
            TypeAdapter(HttpUrl).validate_python(self.value)
        return self


class ContactMethodUpdate(StrictModel):
    value: str | None = Field(None, min_length=1, max_length=2048)
    is_primary: bool | None = None
    is_verified: bool | None = None
    verification_status: VerificationStatus | None = None
    verification_source: str | None = Field(None, max_length=255)
    verified_at: datetime | None = None

    @model_validator(mode="after")
    def validate_verification(self):
        if self.is_verified is True and self.verification_status not in {None, VerificationStatus.VERIFIED}:
            raise ValueError("is_verified requires VERIFIED verification_status")
        if self.verification_status == VerificationStatus.VERIFIED and self.is_verified is False:
            raise ValueError("VERIFIED requires is_verified=true")
        return self


class ContactMethodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contact_id: int
    method_type: ContactMethodType
    value: str
    is_primary: bool
    is_verified: bool
    verification_status: VerificationStatus
    verification_source: str | None
    verified_at: datetime | None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    first_name: str | None
    last_name: str | None
    full_name: str | None
    job_title: str | None
    department: ContactDepartment
    seniority: ContactSeniority
    is_primary: bool
    contact_quality_score: int
    contact_quality_explanation: dict
    methods: list[ContactMethodResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ContactPriorityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contact: ContactResponse
    rank: int
    priority_score: int = Field(ge=0, le=100)
    company_prospect_score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    human_review_required: bool = True


class ContactIntelligenceResponse(BaseModel):
    company_id: int
    organization_id: int
    contacts: list[ContactPriorityResponse] = Field(default_factory=list)
    total: int = Field(ge=0)
    verified_contact_count: int = Field(ge=0)
    missing_intelligence: list[str] = Field(default_factory=list)
    recommended_next_step: str


class DecisionMakerRelevance(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DecisionMakerCompanyResponse(BaseModel):
    company_id: int
    company_name: str | None


class DecisionMakerAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    contact: ContactResponse
    company: DecisionMakerCompanyResponse
    rank: int | None = None
    relevance: DecisionMakerRelevance
    relevance_score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list)
    observed_facts: list[str] = Field(default_factory=list)
    inference: str
    recommendation: str
    uncertainty: list[str] = Field(default_factory=list)
    contact_methods: dict[str, bool]
    contactability_status: str
    commercial_context: dict
    company_prospect_priority: str
    company_prospect_score: int = Field(ge=0, le=100)
    human_review_required: bool = True


class DecisionMakerCompanyAssessmentResponse(BaseModel):
    company_id: int
    organization_id: int
    company_name: str
    prospect_priority: dict
    commercial_context: dict
    contacts: list[DecisionMakerAssessmentResponse] = Field(default_factory=list)
    total: int = Field(ge=0)
    human_review_required: bool = True


class DecisionMakerQueueItemResponse(BaseModel):
    company_name: str
    assessment: DecisionMakerAssessmentResponse


class DecisionMakerQueueResponse(BaseModel):
    items: list[DecisionMakerQueueItemResponse] = Field(default_factory=list)
    total: int = Field(ge=0)
    human_review_required: bool = True


class WarehouseUseCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    warehouse_profile_id: int
    use_case: WarehouseUseCase


class WarehouseProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    warehouse_dependency: WarehouseDependency
    estimated_area_min_sqft: Decimal | None
    estimated_area_max_sqft: Decimal | None
    estimate_confidence: EstimateConfidence
    warehouse_requirement_notes: str | None
    use_cases: list[WarehouseUseCaseResponse] = Field(default_factory=list)


class IntelligenceProfileResponse(IntelligenceProfileWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime


class Page(BaseModel):
    items: list[ContactResponse]
    page: int
    page_size: int
    total: int


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    score: int | None = None
    classification: IcpClassification | None = None
    factors: list[dict] | None = None
    overall_score: int | None = None
    priority: OpportunityPriority | None = None
    warehouse_fit_score: int | None = None
    demand_score: int | None = None
    geographic_score: int | None = None
    contact_score: int | None = None
    explanation: dict | None = None
    calculated_at: datetime


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    action: NextBestActionType
    reason: str
    calculated_at: datetime