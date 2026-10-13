from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.f5_company_intelligence import F5Classification, F5DuplicateStatus, F5Freshness, F5LifecycleStatus, F5PresenceType, F5WarehouseSuitability


class F5ProfileWrite(BaseModel):
    normalized_name: str = Field(min_length=1, max_length=255)
    normalized_domain: str | None = Field(None, max_length=255)
    registration_identifier: str | None = Field(None, max_length=150)
    source_identifier: str | None = Field(None, max_length=255)
    aliases: list[str] = Field(default_factory=list)
    lifecycle_status: F5LifecycleStatus = F5LifecycleStatus.DISCOVERED
    duplicate_status: F5DuplicateStatus = F5DuplicateStatus.NONE
    source: str | None = Field(None, max_length=255)


class F5ProfileResponse(F5ProfileWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class F5PresenceWrite(BaseModel):
    presence_type: F5PresenceType
    region: str = Field(min_length=1, max_length=150)
    city: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = "India"
    classification: F5Classification = F5Classification.UNKNOWN
    confidence: float | None = Field(None, ge=0, le=1)
    observed_at: datetime | None = None
    last_verified_at: datetime | None = None
    freshness: F5Freshness = F5Freshness.UNKNOWN
    source: str | None = None
    source_url: str | None = None
    notes: str | None = None


class F5PresenceResponse(F5PresenceWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    profile_id: int


class F5ClaimWrite(BaseModel):
    claim: str = Field(min_length=1)
    claim_type: str = Field(min_length=1, max_length=100)
    classification: F5Classification
    source: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    published_at: datetime | None = None
    observed_at: datetime | None = None
    last_verified_at: datetime | None = None
    freshness: F5Freshness = F5Freshness.UNKNOWN
    credibility: str | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    confidence_reasons: list[str] = Field(default_factory=list)


class F5ClaimResponse(F5ClaimWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    profile_id: int
    created_at: datetime


class F5AssessmentWrite(BaseModel):
    industry_classification: F5Classification = F5Classification.UNKNOWN
    industry: str | None = None
    warehouse_suitability: F5WarehouseSuitability = F5WarehouseSuitability.UNKNOWN
    icp_classification: str = "UNKNOWN"
    dimensions: dict = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    confidence: float | None = Field(None, ge=0, le=1)
    confidence_reasons: list[str] = Field(default_factory=list)
    freshness: F5Freshness = F5Freshness.UNKNOWN


class F5AssessmentResponse(F5AssessmentWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    evidence_count: int
    calculated_at: datetime


class F5CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_name: str
    legal_name: str | None
    industry: str
    company_type: str
    website: str | None
    headquarters_city: str | None
    headquarters_state: str | None
    profile: F5ProfileResponse | None
    assessment: F5AssessmentResponse | None


class F5CompanyDetail(F5CompanySummary):
    presence: list[F5PresenceResponse] = Field(default_factory=list)
    evidence: list[F5ClaimResponse] = Field(default_factory=list)
    current_warehouse_requirement: dict = {"value": None, "classification": "UNKNOWN"}


class F5CompanyPage(BaseModel):
    items: list[F5CompanySummary]
    page: int
    page_size: int
    total: int