from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.models.lead import LeadPriority, LeadStatus
from app.schemas.lead import (
    LeadCreate,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.lead_intelligence import LeadIntelligenceResponse, PrioritizedLeadResponse
from app.services.lead import LeadService
from app.services.lead_intelligence import LeadIntelligenceService
from app.schemas.follow_up_task import FollowUpTaskResponse, NextActionTaskCreate
from app.services.follow_up_task import FollowUpTaskService

router = APIRouter(
    prefix="/leads",
    tags=["Leads"],
)

lead_service = LeadService()
intelligence_service = LeadIntelligenceService()
task_service = FollowUpTaskService()


@router.post("/{lead_id}/next-action/task", response_model=FollowUpTaskResponse)
def create_next_action_task(
    lead_id: int, task: NextActionTaskCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return task_service.create_from_next_action(db, lead_id, task)


@router.get("/prioritized", response_model=PrioritizedLeadResponse)
def read_prioritized_leads(
    priority: LeadPriority | None = None,
    minimum_score: int = Query(default=0, ge=0, le=100),
    industry: str | None = Query(default=None, min_length=1, max_length=100),
    organization_id: int | None = Query(default=None, ge=1),
    has_active_requirement: bool | None = None,
    status: LeadStatus | None = None,
    research_required: bool | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Live scores, no writes. Excludes won/lost/disqualified unless status is supplied.

    Industry is an exact company-industry filter. Order: priority, score, lead ID.
    Organization is a filter, not an authorization boundary.
    """
    return intelligence_service.list_prioritized_leads(
        db, priority=priority, minimum_score=minimum_score, industry=industry,
        organization_id=organization_id, has_active_requirement=has_active_requirement,
        status=status, research_required=research_required, limit=limit, offset=offset,
    )


@router.post("/{lead_id}/intelligence/calculate", response_model=LeadIntelligenceResponse)
def calculate_lead_intelligence(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Calculate current intelligence and append a score snapshot."""
    result = intelligence_service.create_score_snapshot(db, lead_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result


@router.get("/{lead_id}/intelligence", response_model=LeadIntelligenceResponse)
def read_lead_intelligence(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Evaluate current saved data without persisting a snapshot."""
    result = intelligence_service.calculate_lead_score(db, lead_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result


@router.get("/{lead_id}/intelligence/history", response_model=list[LeadIntelligenceResponse])
def read_lead_intelligence_history(
    lead_id: int,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return immutable evaluations newest first; empty history returns []."""
    results = intelligence_service.list_score_history(db, lead_id, limit=limit, offset=offset)
    if results is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return results


@router.post("/", response_model=LeadResponse)
def create_new_lead(
    lead: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    created = lead_service.create_lead(
        db,
        lead,
    )

    if created is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return created


@router.get("/company/{company_id}", response_model=list[LeadResponse])
def read_leads_by_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return lead_service.list_leads_by_company(
        db,
        company_id,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def read_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = lead_service.get_lead_by_id(
        db,
        lead_id,
    )

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_existing_lead(
    lead_id: int,
    lead: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = lead_service.update_lead(
        db,
        lead_id,
        lead,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return updated


@router.delete("/{lead_id}")
def delete_existing_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = lead_service.delete_lead(
        db,
        lead_id,
    )

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return {
        "message": "Lead deleted successfully"
    }