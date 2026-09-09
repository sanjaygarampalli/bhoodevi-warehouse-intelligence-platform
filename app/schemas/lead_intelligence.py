from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.lead import LeadPriority, LeadStatus


class LeadNextAction(str, Enum):
    RESEARCH_COMPANY = "RESEARCH_COMPANY"
    FIND_DECISION_MAKER = "FIND_DECISION_MAKER"
    RESEARCH_CONTACT = "RESEARCH_CONTACT"
    REVIEW_REQUIREMENT = "REVIEW_REQUIREMENT"
    FIND_WAREHOUSE_MATCH = "FIND_WAREHOUSE_MATCH"
    CONTACT_DECISION_MAKER = "CONTACT_DECISION_MAKER"
    FOLLOW_UP = "FOLLOW_UP"
    MONITOR = "MONITOR"


class LeadMatchEvidence(BaseModel):
    match_id: int
    warehouse_id: int
    requirement_id: int | None
    match_score: float = Field(ge=0, le=100)
    status: str
    model_version: str | None
    requirement_compatibility: str | None
    match_reasons: str | None
    concern_reasons: str | None


class LeadIntelligenceContext(BaseModel):
    """Non-scoring evidence captured in the existing snapshot reasons JSON."""

    action_version: str = "v1"
    recommended_action: LeadNextAction
    action_reason: str
    research_required: bool
    missing_information: list[str]
    limitations: list[str]
    selected_decision_maker_id: int | None
    selected_requirement_id: int | None
    best_warehouse_match: LeadMatchEvidence | None


class LeadComponentScore(BaseModel):
    score: int = Field(ge=0, le=100)
    max_score: int = Field(ge=0, le=100)


class LeadScoringReason(BaseModel):
    factor: str = Field(min_length=1)
    points: int = Field(ge=0, le=100)
    max_points: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1)
    context: LeadIntelligenceContext | None = None


class LeadIntelligenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lead_id: int
    total_score: int = Field(ge=0, le=100)
    priority: LeadPriority
    scoring_version: str = Field(min_length=1, max_length=30)
    reasons: list[LeadScoringReason] = Field(min_length=1)
    calculated_at: datetime

    @computed_field
    @property
    def component_scores(self) -> dict[str, LeadComponentScore]:
        components: dict[str, LeadComponentScore] = {}
        for reason in self.reasons:
            category = reason.factor.split(".", 1)[0]
            component = components.setdefault(category, LeadComponentScore(score=0, max_score=0))
            component.score += reason.points
            component.max_score += reason.max_points
        return components

    @computed_field
    @property
    def positive_signals(self) -> list[str]:
        return [reason.reason for reason in self.reasons if reason.points > 0]

    @computed_field
    @property
    def scoring_gaps(self) -> list[str]:
        # A missing bonus (e.g. urgency) is not necessarily missing information.
        return [reason.reason for reason in self.reasons if reason.points < reason.max_points]

    @computed_field
    @property
    def explanation(self) -> LeadIntelligenceContext | None:
        # Legacy snapshots have no recorded action context. Never infer it from
        # today's database, or retrospectively apply a new action policy.
        return next((reason.context for reason in self.reasons if reason.context is not None), None)

    @field_validator("calculated_at")
    @classmethod
    def normalize_utc(cls, value: datetime) -> datetime:
        # SQLite loses the timezone on round-trip; snapshot timestamps are UTC.
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class PrioritizedLead(BaseModel):
    lead_id: int
    lead_number: str
    company_id: int
    company_name: str | None
    organization_id: int | None
    industry: str | None
    status: LeadStatus
    intelligence: LeadIntelligenceResponse


class PrioritizedLeadResponse(BaseModel):
    items: list[PrioritizedLead]
    total: int = Field(ge=0)
    limit: int
    offset: int
    calculated_at: datetime