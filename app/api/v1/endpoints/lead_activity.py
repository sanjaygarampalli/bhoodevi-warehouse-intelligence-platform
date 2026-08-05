from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.lead_activity import (
    LeadActivityCreate,
    LeadActivityResponse,
    LeadActivityUpdate,
)
from app.services.lead_activity import LeadActivityService

router = APIRouter(
    prefix="/leads/{lead_id}/activities",
    tags=["Lead Activities"],
)

lead_activity_service = LeadActivityService()


@router.post("/", response_model=LeadActivityResponse)
def create_new_lead_activity(
    lead_id: int,
    activity: LeadActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    activity.lead_id = lead_id
    created = lead_activity_service.create_lead_activity(
        db,
        activity,
    )

    if created is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return created


@router.get("/", response_model=list[LeadActivityResponse])
def read_activities_by_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return lead_activity_service.list_activities_by_lead(
        db,
        lead_id,
    )


@router.get("/{activity_id}", response_model=LeadActivityResponse)
def read_lead_activity(
    lead_id: int,
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = lead_activity_service.get_lead_activity_by_id(
        db,
        activity_id,
    )

    if activity is None or activity.lead_id != lead_id:
        raise HTTPException(
            status_code=404,
            detail="Lead Activity not found",
        )

    return activity


@router.put("/{activity_id}", response_model=LeadActivityResponse)
def update_existing_lead_activity(
    lead_id: int,
    activity_id: int,
    activity: LeadActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = lead_activity_service.update_lead_activity(
        db,
        activity_id,
        activity,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Lead Activity not found",
        )

    return updated


@router.delete("/{activity_id}")
def delete_existing_lead_activity(
    lead_id: int,
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = lead_activity_service.delete_lead_activity(
        db,
        activity_id,
    )

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Lead Activity not found",
        )

    return {
        "message": "Lead Activity deleted successfully"
    }