from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.requirement_intelligence import (
    RequirementEvidenceClassification,
    RequirementEvidenceVerificationStatus,
    RequirementFreshness,
)


class RequirementEvidenceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("evidence_date", check_fields=False)
    @classmethod
    def normalize_evidence_date(cls, value):
        from datetime import timezone
        if value is not None and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        if value is not None and value > datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("Evidence date cannot be in the future")
        return value


class RequirementEvidenceCreate(RequirementEvidenceInput):
    source: str = Field(min_length=1, max_length=255)
    source_type: str | None = Field(default=None, max_length=100)
    source_url: str | None = Field(default=None, max_length=2048)
    observed_evidence: str = Field(min_length=1)
    inference: str | None = None
    classification: RequirementEvidenceClassification
    evidence_date: datetime | None = None
    verification_status: RequirementEvidenceVerificationStatus = RequirementEvidenceVerificationStatus.UNVERIFIED
    confidence: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class RequirementEvidenceUpdate(RequirementEvidenceInput):
    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in ("source", "observed_evidence", "classification", "verification_status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self

    source: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: str | None = Field(default=None, max_length=100)
    source_url: str | None = Field(default=None, max_length=2048)
    observed_evidence: str | None = Field(default=None, min_length=1)
    inference: str | None = None
    classification: RequirementEvidenceClassification | None = None
    evidence_date: datetime | None = None
    verification_status: RequirementEvidenceVerificationStatus | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class RequirementEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    requirement_id: int
    source: str
    source_type: str | None
    source_url: str | None
    observed_evidence: str
    inference: str | None
    classification: RequirementEvidenceClassification
    evidence_date: datetime | None
    verification_status: RequirementEvidenceVerificationStatus
    verified_at: datetime | None
    verified_by_user_id: int | None
    confidence: Decimal | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class RequirementAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None
    organization_id: int
    requirement_id: int
    requirement_confidence: Decimal | None
    geography_confidence: Decimal | None
    size_confidence: Decimal | None
    timing_confidence: Decimal | None
    operational_confidence: Decimal | None
    commercial_confidence: Decimal | None
    evidence_strength: Decimal | None
    reasons: list[str]
    freshness: RequirementFreshness
    freshness_anchor: datetime | None
    calculated_at: datetime


class RequirementIntelligenceResponse(BaseModel):
    organization_id: int
    requirement: "RequirementResponse"
    company_name: str
    evidence: list[RequirementEvidenceResponse]
    assessment: RequirementAssessmentResponse | None
    market_signal_ids: list[int]


from app.schemas.requirement import RequirementResponse  # noqa: E402

RequirementIntelligenceResponse.model_rebuild()
