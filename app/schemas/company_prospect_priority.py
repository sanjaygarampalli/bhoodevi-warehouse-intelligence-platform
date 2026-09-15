from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.prospect_prioritization import PriorityLevel


class CommercialContext(BaseModel):
    existing_lead: bool
    existing_requirement: bool
    active_deal: bool
    pipeline_status: str


class ScoreReason(BaseModel):
    points: int
    reason: str


class CompanyProspectPriority(BaseModel):
    company_id: int
    organization_id: int
    company_name: str
    priority: PriorityLevel
    priority_score: int = Field(ge=0, le=100)
    demand_strength: str
    evidence_confidence: str
    observed_facts: list[str] = Field(default_factory=list)
    demand_indicators: list[str] = Field(default_factory=list)
    commercial_context: CommercialContext
    inference: str
    uncertainties: list[str] = Field(default_factory=list)
    recommended_next_action: str
    human_review_required: bool
    score_reasons: list[ScoreReason] = Field(default_factory=list)
    evaluated_at: datetime


class CompanyProspectPriorityList(BaseModel):
    items: list[CompanyProspectPriority] = Field(default_factory=list)
    total: int = Field(ge=0)
    evaluated_at: datetime