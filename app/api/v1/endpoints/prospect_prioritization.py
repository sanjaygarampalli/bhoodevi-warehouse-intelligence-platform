"""Read-only API endpoints for deterministic prospect prioritization."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
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


@router.get("/dashboard", response_model=PriorityDashboardSummary)
def read_priority_dashboard(
    organization_id: int | None = Query(default=None, ge=1),
    top_n: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregate priority counts and the top leads/opportunities."""
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
    result = prioritization_service.evaluate_opportunity(db, deal_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result
