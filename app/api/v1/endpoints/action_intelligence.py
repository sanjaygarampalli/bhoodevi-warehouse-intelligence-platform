"""Authenticated, read-only action queue endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.organization_access import require_organization_access
from app.schemas.action_intelligence import (
    ActionIntelligenceSummaryResponse, ActionRecommendationListResponse, ActionType,
)
from app.schemas.prospect_prioritization import PriorityLevel
from app.services.action_intelligence import ActionIntelligenceService

router = APIRouter(prefix="/action-intelligence", tags=["Action Intelligence"])
action_service = ActionIntelligenceService()


@router.get("/summary", response_model=ActionIntelligenceSummaryResponse)
def read_action_summary(organization_id: int | None = Query(None, ge=1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if organization_id is not None: require_organization_access(db, current_user, organization_id)
    return action_service.get_action_summary(db, organization_id=organization_id)


@router.get("/actions", response_model=ActionRecommendationListResponse)
def read_actions(
    priority: PriorityLevel | None = None,
    action_type: ActionType | None = None,
    limit: int = Query(default=20, ge=1, le=100), organization_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if organization_id is not None: require_organization_access(db, current_user, organization_id)
    return action_service.get_prioritized_actions(db, limit=limit, priority=priority, action_type=action_type, organization_id=organization_id)


@router.get("/today", response_model=ActionRecommendationListResponse)
def read_today_actions(
    limit: int = Query(default=20, ge=1, le=50), organization_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if organization_id is not None: require_organization_access(db, current_user, organization_id)
    return action_service.get_today_actions(db, limit=limit, organization_id=organization_id)


@router.get("/leads/{lead_id}", response_model=ActionRecommendationListResponse)
def read_lead_actions(
    lead_id: int, limit: int = Query(default=20, ge=1, le=100), organization_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    if organization_id is not None: require_organization_access(db, current_user, organization_id)
    return action_service.get_lead_actions(db, lead_id, limit=limit, organization_id=organization_id)