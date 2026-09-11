"""API contracts for the read-only action and follow-up intelligence queue."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.prospect_prioritization import PriorityLevel


class ActionType(str, Enum):
    CONTACT_LEAD = "CONTACT_LEAD"
    FOLLOW_UP = "FOLLOW_UP"
    FOLLOW_UP_OVERDUE = "FOLLOW_UP_OVERDUE"
    CONTACT_DECISION_MAKER = "CONTACT_DECISION_MAKER"
    REVIEW_HIGH_MATCH = "REVIEW_HIGH_MATCH"
    ADVANCE_DEAL = "ADVANCE_DEAL"
    DEAL_AT_RISK = "DEAL_AT_RISK"
    REENGAGE_COLD_LEAD = "REENGAGE_COLD_LEAD"
    REVIEW_REQUIREMENT = "REVIEW_REQUIREMENT"
    SCHEDULE_DISCUSSION = "SCHEDULE_DISCUSSION"


class ActionRecommendationResponse(BaseModel):
    id: str
    action_type: ActionType
    priority: PriorityLevel
    title: str
    reason: str
    recommended_action: str
    lead_id: int | None = None
    lead_name: str | None = None
    company_id: int | None = None
    company_name: str | None = None
    decision_maker_id: int | None = None
    decision_maker_name: str | None = None
    deal_id: int | None = None
    follow_up_task_id: int | None = None
    warehouse_match_id: int | None = None
    requirement_id: int | None = None
    due_at: datetime | None = None
    source_at: datetime | None = None
    ranking_score: int = Field(ge=0)


class ActionIntelligenceSummaryResponse(BaseModel):
    total_actions: int = Field(ge=0)
    critical_actions: int = Field(ge=0)
    high_priority_actions: int = Field(ge=0)
    overdue_follow_ups: int = Field(ge=0)
    stale_leads: int = Field(ge=0)
    deals_at_risk: int = Field(ge=0)
    warehouse_opportunities_requiring_attention: int = Field(ge=0)
    evaluated_at: datetime


class ActionRecommendationListResponse(BaseModel):
    items: list[ActionRecommendationResponse] = Field(default_factory=list)
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    evaluated_at: datetime