from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.deal import DealCreate, DealResponse, DealStageHistoryResponse, DealTransition, DealUpdate
from app.services.deal import DealService
from app.schemas.opportunity import OpportunitySummary
from app.services.opportunity import OpportunityService

router = APIRouter(prefix="/deals", tags=["Deals"])
deal_service = DealService()
opportunity_service = OpportunityService()


@router.get("/", response_model=list[DealResponse])
def list_deals(
    stage_id: int | None = Query(None, gt=0), lead_id: int | None = Query(None, gt=0),
    organization_id: int | None = Query(None, gt=0), is_active: bool | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return deal_service.list_deals(db, stage_id=stage_id, lead_id=lead_id, organization_id=organization_id,
                                   is_active=is_active, skip=skip, limit=limit)


@router.post("/", response_model=DealResponse)
def create_deal(
    deal: DealCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return deal_service.create_deal(db, deal, changed_by_user_id=current_user.id)


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return deal_service.get_deal(db, deal_id)


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int, deal: DealUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return deal_service.update_deal(db, deal_id, deal)


@router.post("/{deal_id}/transition", response_model=DealResponse)
def transition_deal(
    deal_id: int, transition: DealTransition,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return deal_service.transition_deal(db, deal_id, transition, changed_by_user_id=current_user.id)


@router.get("/{deal_id}/history", response_model=list[DealStageHistoryResponse])
def get_history(
    deal_id: int, skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return deal_service.get_history(db, deal_id, skip=skip, limit=limit)


@router.get("/{deal_id}/opportunity", response_model=OpportunitySummary)
def get_opportunity(
    deal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """Integrated, read-only opportunity context for a deal the user can read."""
    return opportunity_service.get_opportunity(db, deal_id)