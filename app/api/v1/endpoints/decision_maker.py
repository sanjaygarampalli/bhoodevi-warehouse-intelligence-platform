from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.decision_maker import (
    DecisionMakerCreate,
    DecisionMakerResponse,
    DecisionMakerUpdate,
)
from app.services.decision_maker import DecisionMakerService

router = APIRouter(
    prefix="/decision-makers",
    tags=["Decision Makers"],
)

decision_maker_service = DecisionMakerService()


@router.post("/", response_model=DecisionMakerResponse)
def create_new_decision_maker(
    decision_maker: DecisionMakerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    created = decision_maker_service.create_decision_maker(
        db,
        decision_maker,
    )

    if created is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return created


@router.get("/company/{company_id}", response_model=list[DecisionMakerResponse])
def read_decision_makers_by_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return decision_maker_service.list_decision_makers_by_company(
        db,
        company_id,
    )


@router.get("/{decision_maker_id}", response_model=DecisionMakerResponse)
def read_decision_maker(
    decision_maker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    decision_maker = decision_maker_service.get_decision_maker_by_id(
        db,
        decision_maker_id,
    )

    if decision_maker is None:
        raise HTTPException(
            status_code=404,
            detail="Decision maker not found",
        )

    return decision_maker


@router.put("/{decision_maker_id}", response_model=DecisionMakerResponse)
def update_existing_decision_maker(
    decision_maker_id: int,
    decision_maker: DecisionMakerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = decision_maker_service.update_decision_maker(
        db,
        decision_maker_id,
        decision_maker,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Decision maker not found",
        )

    return updated


@router.delete("/{decision_maker_id}")
def delete_existing_decision_maker(
    decision_maker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = decision_maker_service.delete_decision_maker(
        db,
        decision_maker_id,
    )

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Decision maker not found",
        )

    return {
        "message": "Decision maker deleted successfully"
    }