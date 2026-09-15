"""Read-only API endpoints for deterministic prospect prioritization."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.organization_access import organization_for_lead, require_organization_access
from app.schemas.lead import LeadStatus
from app.schemas.prospect_prioritization import (
    LeadPriorityListResponse,
    LeadPriorityResult,
    OpportunityPriorityListResponse,
    OpportunityPriorityResult,
    PriorityDashboardSummary,
)
from app.services.prospect_prioritization import ProspectPrioritizationService

router = APIRouter(
    prefix="/prospect-prioritization",
    tags=["Prospect Prioritization"],
)

prioritization_service = ProspectPrioritizationService()


def _organization_context(db, current_user, organization_id):
    if organization_id is None and current_user.role != "admin":
        raise HTTPException(status_code=400, detail="organization_id is required")
    if organization_id is not None:
        require_organization_access(db, current_user, organization_id)


@router.get("/dashboard", response_model=PriorityDashboardSummary)
def read_priority_dashboard(
    organization_id: int | None = Query(default=None, ge=1),
    top_n: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregate priority counts and the top leads/opportunities."""
    _organization_context(db, current_user, organization_id)
    return prioritization_service.dashboard_summary(
        db, organization_id=organization_id, top_n=top_n,
    )


@router.get("/leads", response_model=LeadPriorityListResponse)
def list_priority_leads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    industry: str | None = Query(default=None, min_length=1, max_length=100),
    organization_id: int | None = Query(default=None, ge=1),
    has_active_requirement: bool | None = None,
    status: LeadStatus | None = None,
    minimum_priority_score: int = Query(default=0, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return ranked lead priorities without persisting a snapshot."""
    _organization_context(db, current_user, organization_id)
    return prioritization_service.list_lead_priorities(
        db,
        limit=limit,
        offset=offset,
        industry=industry,
        organization_id=organization_id,
        has_active_requirement=has_active_requirement,
        status=status.value if status else None,
        minimum_priority_score=minimum_priority_score,
    )


@router.get("/leads/{lead_id}", response_model=LeadPriorityResult)
def read_priority_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the deterministic priority evaluation for one lead."""
    resolved_organization_id = organization_for_lead(db, lead_id)
    if resolved_organization_id is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    require_organization_access(db, current_user, resolved_organization_id)
    result = prioritization_service.evaluate_lead(db, lead_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result


@router.get("/opportunities", response_model=OpportunityPriorityListResponse)
def list_priority_opportunities(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    organization_id: int | None = Query(default=None, ge=1),
    minimum_priority_score: int = Query(default=0, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return ranked deal/opportunity priorities."""
    _organization_context(db, current_user, organization_id)
    return prioritization_service.list_opportunity_priorities(
        db,
        limit=limit,
        offset=offset,
        organization_id=organization_id,
        minimum_priority_score=minimum_priority_score,
    )


@router.get("/opportunities/{deal_id}", response_model=OpportunityPriorityResult)
def read_priority_opportunity(
    deal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the deterministic priority evaluation for one deal."""
    from app.models.deal import Deal
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    require_organization_access(db, current_user, deal.organization_id)
    result = prioritization_service.evaluate_opportunity(db, deal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result
