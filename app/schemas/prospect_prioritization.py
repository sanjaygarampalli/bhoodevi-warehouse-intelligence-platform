"""Schemas for the Prospect Prioritization Engine.

Transforms existing BWIP intelligence data into a practical business-development
priority system that helps users understand who to contact, who to follow up
with, who is becoming cold, and which opportunity is most valuable.
"""

from datetime import datetime
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel, Field


# ── Priority Level ───────────────────────────────────────────────────────

class PriorityLevel(str, Enum):
    """Business priority classification for prospects and opportunities."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Next Best Action ─────────────────────────────────────────────────────

class NextBestActionType(str, Enum):
    """Deterministic, explainable next action for a prospect.

    Each action is derived purely from existing BWIP data fields, never from
    invented predictions or external AI calls.
    """
    CONTACT_IMMEDIATELY = "CONTACT_IMMEDIATELY"
    FOLLOW_UP_TODAY = "FOLLOW_UP_TODAY"
    FOLLOW_UP_OVERDUE = "FOLLOW_UP_OVERDUE"
    QUALIFY_REQUIREMENT = "QUALIFY_REQUIREMENT"
    FIND_DECISION_MAKER = "FIND_DECISION_MAKER"
    CREATE_WAREHOUSE_MATCH = "CREATE_WAREHOUSE_MATCH"
    ADVANCE_DEAL = "ADVANCE_DEAL"
    REENGAGE_LEAD = "REENGAGE_LEAD"
    MONITOR = "MONITOR"


# ── Priority Factors ─────────────────────────────────────────────────────

class PriorityFactor(BaseModel):
    """One scoring factor that contributed to the overall priority."""
    name: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=200)
    weight: int = Field(ge=0, le=100)
    score: int = Field(ge=0, le=100)
    reason: str = Field(min_length=1, max_length=500)


class PriorityReason(BaseModel):
    """A human-readable explanation of why a prospect received its priority."""
    factor: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=1, max_length=500)
    impact: str = Field(min_length=1, max_length=100)


# ── Next Best Action ─────────────────────────────────────────────────────

class NextBestAction(BaseModel):
    """The recommended next action for a prioritized prospect.

    Includes the action type, a business-readable summary, the reasoning
    behind the recommendation, and optional reference IDs.
    """
    action: NextBestActionType
    summary: str = Field(min_length=1, max_length=400)
    reason: str = Field(min_length=1, max_length=1000)
    reference_id: int | None = None
    reference_type: str | None = None  # e.g. "task", "deal", "requirement"


# ── Lead Priority Result ─────────────────────────────────────────────────

class LeadPriorityResult(BaseModel):
    """Full priority result for a single lead/prospect."""
    lead_id: int
    lead_number: str
    company_id: int
    company_name: str | None
    organization_id: int | None
    industry: str | None
    lead_status: str
    priority_level: PriorityLevel
    priority_score: int = Field(ge=0, le=100)
    factors: list[PriorityFactor] = Field(default_factory=list)
    reasons: list[PriorityReason] = Field(default_factory=list)
    next_best_action: NextBestAction | None
    intelligence_score: int | None
    follow_up_overdue: bool
    has_active_requirement: bool
    has_viable_warehouse_match: bool
    opportunity_id: int | None
    evaluated_at: datetime


# ── Opportunity Priority Result ──────────────────────────────────────────

class OpportunityPriorityResult(BaseModel):
    """Full priority result for a single opportunity (deal)."""
    deal_id: int
    deal_name: str
    organization_id: int
    organization_name: str | None
    lead_id: int
    lead_number: str | None
    stage_name: str
    deal_status: str
    expected_revenue: Decimal | None
    priority_level: PriorityLevel
    priority_score: int = Field(ge=0, le=100)
    factors: list[PriorityFactor] = Field(default_factory=list)
    reasons: list[PriorityReason] = Field(default_factory=list)
    next_best_action: NextBestAction | None
    intelligence_score: int | None
    overdue_task_count: int
    days_in_stage: int | None
    evaluated_at: datetime


# ── Dashboard Summary ────────────────────────────────────────────────────

class PriorityDashboardSummary(BaseModel):
    """Summary counts across all priorities for quick decision-making."""
    total_leads: int
    critical_leads: int
    high_priority_leads: int
    medium_priority_leads: int
    low_priority_leads: int
    overdue_follow_ups: int
    leads_requiring_contact: int
    opportunities_ready_to_advance: int
    top_lead_priorities: list[LeadPriorityResult] = Field(default_factory=list)
    top_opportunity_priorities: list[OpportunityPriorityResult] = Field(default_factory=list)
    evaluated_at: datetime


# ── List Response Wrappers ───────────────────────────────────────────────

class LeadPriorityListResponse(BaseModel):
    items: list[LeadPriorityResult] = Field(default_factory=list)
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    evaluated_at: datetime


class OpportunityPriorityListResponse(BaseModel):
    items: list[OpportunityPriorityResult] = Field(default_factory=list)
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    evaluated_at: datetime