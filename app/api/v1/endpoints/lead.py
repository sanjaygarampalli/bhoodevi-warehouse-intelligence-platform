from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.lead import (
    LeadCreate,
    LeadResponse,
    LeadUpdate,
)
from app.services.lead import LeadService

router = APIRouter(
    prefix="/leads",
    tags=["Leads"],
)

lead_service = LeadService()


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