from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.market_signal import (
    DemandStrength,
    EvidenceCredibility,
    MarketSignalConfidence,
    MarketSignalSourceType,
    MarketSignalStatus,
    MarketSignalType,
    RequirementCandidateStatus,
)


class MarketSignalCreate(BaseModel):
    organization_id: int = Field(..., gt=0)
    company_id: int | None = Field(default=None, gt=0)
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    signal_type: MarketSignalType
    source_type: MarketSignalSourceType
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2048)
    source_published_at: datetime | None = None
    detected_at: datetime | None = None
    location_text: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    announced_investment_amount: Decimal | None = Field(default=None, ge=0)
    announced_investment_currency: str | None = Field(default=None, min_length=3, max_length=3)
    confidence_level: MarketSignalConfidence = MarketSignalConfidence.LOW


class MarketSignalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    signal_type: MarketSignalType | None = None
    source_type: MarketSignalSourceType | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2048)
    source_published_at: datetime | None = None
    location_text: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    announced_investment_amount: Decimal | None = Field(default=None, ge=0)
    announced_investment_currency: str | None = Field(default=None, min_length=3, max_length=3)
    confidence_level: MarketSignalConfidence | None = None


class MarketSignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    company_id: int | None
    title: str
    description: str | None
    signal_type: MarketSignalType
    status: MarketSignalStatus
    source_type: MarketSignalSourceType
    source_name: str | None
    source_url: str | None
    source_published_at: datetime | None
    detected_at: datetime
    location_text: str | None
    city: str | None
    district: str | None
    state: str | None
    country: str | None
    announced_investment_amount: Decimal | None
    announced_investment_currency: str | None
    confidence_level: MarketSignalConfidence
    created_by_user_id: int | None
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime
    updated_at: datetime


class MarketSignalEvidenceCreate(BaseModel):
    evidence_type: MarketSignalSourceType
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2048)
    title: str = Field(..., min_length=1, max_length=255)
    excerpt: str | None = None
    published_at: datetime | None = None
    recorded_at: datetime | None = None
    credibility_level: EvidenceCredibility


class MarketSignalEvidenceUpdate(BaseModel):
    evidence_type: MarketSignalSourceType | None = None
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=2048)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    excerpt: str | None = None
    published_at: datetime | None = None
    credibility_level: EvidenceCredibility | None = None


class MarketSignalEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    market_signal_id: int
    evidence_type: MarketSignalSourceType
    source_name: str | None
    source_url: str | None
    title: str
    excerpt: str | None
    published_at: datetime | None
    recorded_at: datetime
    credibility_level: EvidenceCredibility
    created_at: datetime
    updated_at: datetime


class MarketSignalAssessmentResponse(BaseModel):
    market_signal_id: int
    indicates_potential_warehouse_demand: bool
    demand_strength: DemandStrength
    confidence_level: MarketSignalConfidence
    explanation: str
    reasons: list[str]
    recommended_next_step: str
    observed_evidence: list[str]
    inference: str
    recommendation: str


class RequirementCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    company_id: int
    market_signal_id: int
    status: RequirementCandidateStatus
    demand_strength: DemandStrength
    confidence_level: MarketSignalConfidence
    summary: str
    reasoning: str
    city: str | None
    district: str | None
    state: str | None
    country: str | None
    created_at: datetime
    updated_at: datetime
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None


class RequirementCandidateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str | None = Field(default=None, min_length=1, max_length=500)
    reasoning: str | None = None


class MarketSignalTransition(BaseModel):
    target_status: MarketSignalStatus
    review_notes: str | None = Field(default=None, max_length=5000)


class RequirementCandidateTransition(BaseModel):
    target_status: RequirementCandidateStatus