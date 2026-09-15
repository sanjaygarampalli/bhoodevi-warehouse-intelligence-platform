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
from app.schemas.company_prospect_priority import CompanyProspectPriority, CompanyProspectPriorityList
from app.services.company_prospect_priority import CompanyProspectPriorityService
from app.services.organization_access import require_organization_access, require_organization_write

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)

company_service = CompanyService()
prospect_priority_service = CompanyProspectPriorityService()


@router.post("/", response_model=CompanyResponse)
def create_new_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        require_organization_write(db, current_user, company.organization_id)
        return company_service.create_company(db, company)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/prospect-priorities", response_model=CompanyProspectPriorityList)
def list_company_prospect_priorities(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_organization_access(db, current_user, organization_id)
    return prospect_priority_service.list(db, organization_id)


@router.get("/{company_id}/prospect-priority", response_model=CompanyProspectPriority)
def read_company_prospect_priority(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = company_service.get_company_by_id(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_access(db, current_user, company.organization_id)
    return prospect_priority_service.assess(db, company_id)


@router.get("/", response_model=list[CompanyResponse])
def read_all_companies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        return company_service.list_companies(db)
    from sqlalchemy import select
    from app.models.company import Company
    from app.models.organization_membership import OrganizationMembership, MembershipStatus
    return list(db.scalars(select(Company).join(OrganizationMembership, OrganizationMembership.organization_id == Company.organization_id).where(
        OrganizationMembership.user_id == current_user.id,
        OrganizationMembership.status == MembershipStatus.ACTIVE,
    )))


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

    require_organization_access(db, current_user, company.organization_id)

    return company


@router.put("/{company_id}", response_model=CompanyResponse)
def update_existing_company(
    company_id: int,
    company: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = company_service.get_company_by_id(db, company_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_write(db, current_user, existing.organization_id)
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
    current_user: User = Depends(get_current_user),
):
    existing = company_service.get_company_by_id(db, company_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_write(db, current_user, existing.organization_id)
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