"""Schemas for the BWIP operational intelligence dashboard."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class AttentionItem(BaseModel):
    entity_type: str
    entity_id: int
    title: str
    priority: str
    recommended_action: str
    reason: str
    relevant_date: datetime | None = None


class ExecutiveSummary(BaseModel):
    total_active_leads: int = Field(ge=0)
    critical_priority_leads: int = Field(ge=0)
    high_priority_leads: int = Field(ge=0)
    overdue_follow_ups: int = Field(ge=0)
    follow_ups_due_today: int = Field(ge=0)
    active_opportunities: int = Field(ge=0)
    active_deals: int = Field(ge=0)
    deals_at_risk: int = Field(ge=0)
    strong_warehouse_matches: int = Field(ge=0)
    new_leads: int = Field(ge=0)


class PipelineStageSummary(BaseModel):
    stage_id: int
    stage_key: str
    stage_name: str
    stage_order: int
    active_deals: int = Field(ge=0)
    total_deals: int = Field(ge=0)
    expected_revenue: Decimal | None = None


class PipelineSummary(BaseModel):
    stages: list[PipelineStageSummary] = Field(default_factory=list)
    active_deals: int = Field(ge=0)
    won_deals: int = Field(ge=0)
    lost_deals: int = Field(ge=0)
    deals_requiring_follow_up: int = Field(ge=0)
    potential_opportunities: int = Field(ge=0)


class LeadHealthSummary(BaseModel):
    high_intelligence_leads: int = Field(ge=0)
    medium_intelligence_leads: int = Field(ge=0)
    low_intelligence_leads: int = Field(ge=0)
    leads_with_recent_activity: int = Field(ge=0)
    leads_becoming_inactive: int = Field(ge=0)
    leads_without_decision_makers: int = Field(ge=0)
    leads_without_requirements: int = Field(ge=0)
    leads_needing_qualification: int = Field(ge=0)


class WarehouseOpportunityItem(BaseModel):
    lead_id: int
    requirement_id: int | None
    match_id: int
    match_score: Decimal
    status: str
    top_reason: str | None = None


class WarehouseOpportunitySummary(BaseModel):
    strong_matches: int = Field(ge=0)
    leads_with_matching_potential: int = Field(ge=0)
    requirements_needing_matching: int = Field(ge=0)
    top_opportunities: list[WarehouseOpportunityItem] = Field(default_factory=list)


class PriorityDashboardItem(BaseModel):
    entity_type: str
    entity_id: int
    name: str
    priority_level: str
    priority_score: int = Field(ge=0, le=100)
    recommended_action: str
    reason: str


class RecentActivityItem(BaseModel):
    entity_type: str
    entity_id: int
    lead_id: int | None = None
    activity_type: str
    title: str
    occurred_at: datetime
    outcome: str | None = None


class OperationalDashboard(BaseModel):
    generated_at: datetime
    executive_summary: ExecutiveSummary
    todays_attention: list[AttentionItem] = Field(default_factory=list)
    pipeline_summary: PipelineSummary
    lead_health: LeadHealthSummary
    warehouse_opportunities: WarehouseOpportunitySummary
    top_priorities: list[PriorityDashboardItem] = Field(default_factory=list)
    recent_activity: list[RecentActivityItem] = Field(default_factory=list)
