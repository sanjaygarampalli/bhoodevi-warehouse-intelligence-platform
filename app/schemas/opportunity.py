"""Read-only integrated opportunity (Deal) context built from existing schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.deal import DealResponse
from app.schemas.follow_up_task import FollowUpTaskResponse
from app.schemas.lead import LeadResponse
from app.schemas.lead_intelligence import LeadIntelligenceResponse
from app.schemas.requirement import RequirementResponse
from app.schemas.warehouse_match import WarehouseMatchResponse
from app.models.organization import OrgType, OrganizationStatus, SubscriptionTier


class NextActionItem(BaseModel):
    """Deterministic, explainable next step; never an invented prediction."""

    type: str = Field(min_length=1, max_length=40)
    summary: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=2000)
    reference_id: int | None = None
    due_at: datetime | None = None


class OpportunityOrganization(BaseModel):
    """Scalar-only organization context (no relationship traversal)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_code: str
    legal_name: str
    trading_name: str | None
    org_type: OrgType
    subscription_tier: SubscriptionTier
    status: OrganizationStatus
    city: str | None
    state: str | None
    country: str


class OpportunitySummary(BaseModel):
    deal: DealResponse
    organization: OpportunityOrganization
    lead: LeadResponse
    requirement: RequirementResponse
    selected_warehouse_match: WarehouseMatchResponse | None
    warehouse_matches: list[WarehouseMatchResponse] = Field(default_factory=list)
    open_tasks: list[FollowUpTaskResponse] = Field(default_factory=list)
    overdue_tasks: list[FollowUpTaskResponse] = Field(default_factory=list)
    upcoming_tasks: list[FollowUpTaskResponse] = Field(default_factory=list)
    intelligence: LeadIntelligenceResponse | None
    next_action: NextActionItem | None
    generated_at: datetime