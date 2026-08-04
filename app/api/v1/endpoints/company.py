from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.company import CompanyService

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)

company_service = CompanyService()


@router.post("/", response_model=CompanyResponse)
def create_new_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    return company_service.create_company(
        db,
        company,
    )


@router.get("/", response_model=list[CompanyResponse])
def read_all_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return company_service.list_companies(db)


@router.get("/{company_id}", response_model=CompanyResponse)
def read_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = company_service.get_company_by_id(
        db,
        company_id,
    )

    if company is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_existing_company(
    company_id: int,
    company: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = company_service.update_company(
        db,
        company_id,
        company,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return updated


@router.delete("/{company_id}")
def delete_existing_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = company_service.delete_company(
        db,
        company_id,
    )

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Company not found",
        )

    return {
        "message": "Company deleted successfully"
    }