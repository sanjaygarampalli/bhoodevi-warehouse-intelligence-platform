from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.deal import DealCreate, DealResponse, DealStageHistoryResponse, DealTransition, DealUpdate
from app.services.deal import DealService
from app.schemas.opportunity import OpportunitySummary
from app.services.opportunity import OpportunityService
from app.services.follow_up_task import FollowUpTaskService
from app.services.lead_activity import LeadActivityConflict, LeadActivityService
from app.schemas.follow_up_task import DealFollowUpTaskCreate, FollowUpTaskCreate, FollowUpTaskResponse
from app.schemas.lead_activity import DealActivityCreate, LeadActivityCreate, LeadActivityResponse
from app.services.organization_access import require_organization_access, require_organization_write

router = APIRouter(prefix="/deals", tags=["Deals"])
deal_service = DealService()
opportunity_service = OpportunityService()
execution_activity_service = LeadActivityService()
execution_task_service = FollowUpTaskService()


def _deal_execution_context(db, current_user, deal_id):
    deal = deal_service.get_deal(db, deal_id)
    require_organization_access(db, current_user, deal.organization_id)
    return deal


@router.post("/{deal_id}/activities", response_model=LeadActivityResponse)
def create_deal_activity(
    deal_id: int, activity: DealActivityCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    deal = _deal_execution_context(db, current_user, deal_id)
    data = activity.model_dump()
    data.update(lead_id=deal.lead_id, deal_id=deal.id, performed_by=current_user.id)
    try:
        return execution_activity_service.create_lead_activity(db, LeadActivityCreate(**data))
    except LeadActivityConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{deal_id}/activities", response_model=list[LeadActivityResponse])
def list_deal_activities(
    deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _deal_execution_context(db, current_user, deal_id)
    return execution_activity_service.list_activities_by_deal(db, deal_id)


@router.post("/{deal_id}/follow-up-tasks", response_model=FollowUpTaskResponse)
def create_deal_follow_up_task(
    deal_id: int, task: DealFollowUpTaskCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    deal = _deal_execution_context(db, current_user, deal_id)
    data = task.model_dump()
    data.update(lead_id=deal.lead_id, deal_id=deal.id)
    return execution_task_service.create_task(db, FollowUpTaskCreate(**data))


@router.get("/{deal_id}/follow-up-tasks", response_model=list[FollowUpTaskResponse])
def list_deal_follow_up_tasks(
    deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _deal_execution_context(db, current_user, deal_id)
    return execution_task_service.list_tasks(db, deal_id=deal_id)


@router.get("/", response_model=list[DealResponse])
def list_deals(
    stage_id: int | None = Query(None, gt=0), lead_id: int | None = Query(None, gt=0),
    organization_id: int | None = Query(None, gt=0), is_active: bool | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if organization_id is not None:
        require_organization_access(db, current_user, organization_id)
    elif current_user.role != "admin":
        raise HTTPException(status_code=400, detail="organization_id is required")
    return deal_service.list_deals(db, stage_id=stage_id, lead_id=lead_id, organization_id=organization_id,
                                   is_active=is_active, skip=skip, limit=limit)


@router.post("/", response_model=DealResponse)
def create_deal(
    deal: DealCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    organization_id = deal_service._boundaries(
        db, deal.lead_id, deal.requirement_id, deal.selected_warehouse_match_id,
    )
    require_organization_write(db, current_user, organization_id)
    return deal_service.create_deal(db, deal, changed_by_user_id=current_user.id)


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    deal = deal_service.get_deal(db, deal_id)
    require_organization_access(db, current_user, deal.organization_id)
    return deal


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int, deal: DealUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    existing = _deal_execution_context(db, current_user, deal_id)
    require_organization_write(db, current_user, existing.organization_id)
    return deal_service.update_deal(db, deal_id, deal)


@router.post("/{deal_id}/transition", response_model=DealResponse)
def transition_deal(
    deal_id: int, transition: DealTransition,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    existing = _deal_execution_context(db, current_user, deal_id)
    require_organization_write(db, current_user, existing.organization_id)
    return deal_service.transition_deal(db, deal_id, transition, changed_by_user_id=current_user.id)


@router.get("/{deal_id}/history", response_model=list[DealStageHistoryResponse])
def get_history(
    deal_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    _deal_execution_context(db, current_user, deal_id)
    return deal_service.get_history(db, deal_id, skip=skip, limit=limit)


@router.get("/{deal_id}/opportunity", response_model=OpportunitySummary)
def get_opportunity(
    deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """Integrated, read-only opportunity context for a deal the user can read."""
    _deal_execution_context(db, current_user, deal_id)
    return opportunity_service.get_opportunity(db, deal_id)