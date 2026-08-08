from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.requirement import (
    RequirementCreate,
    RequirementResponse,
    RequirementUpdate,
)
from app.services.requirement import RequirementService

router = APIRouter(
    prefix="/leads/{lead_id}/requirements",
    tags=["Requirements"],
)

requirement_service = RequirementService()


@router.post("/", response_model=RequirementResponse)
def create_new_requirement(
    lead_id: int,
    requirement: RequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    requirement.lead_id = lead_id
    created = requirement_service.create_requirement(
        db,
        requirement,
    )

    if created is None:
        raise HTTPException(
            status_code=404,
            detail="Lead not found",
        )

    return created


@router.get("/", response_model=list[RequirementResponse])
def read_requirements_by_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return requirement_service.list_requirements_by_lead(
        db,
        lead_id,
    )


@router.get("/{requirement_id}", response_model=RequirementResponse)
def read_requirement(
    lead_id: int,
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    requirement = requirement_service.get_requirement_by_id(
        db,
        requirement_id,
    )

    if requirement is None or requirement.lead_id != lead_id:
        raise HTTPException(
            status_code=404,
            detail="Requirement not found",
        )

    return requirement


@router.put("/{requirement_id}", response_model=RequirementResponse)
def update_existing_requirement(
    lead_id: int,
    requirement_id: int,
    requirement: RequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = requirement_service.update_requirement(
        db,
        requirement_id,
        requirement,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Requirement not found",
        )

    return updated


@router.delete("/{requirement_id}")
def delete_existing_requirement(
    lead_id: int,
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = requirement_service.delete_requirement(
        db,
        requirement_id,
    )

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Requirement not found",
        )

    return {
        "message": "Requirement deleted successfully"
    }