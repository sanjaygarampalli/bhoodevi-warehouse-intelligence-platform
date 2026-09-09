from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Organizations"])

organization_service = OrganizationService()


@router.post("/", response_model=OrganizationResponse)
def create_new_organization(
    organization: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    try:
        return organization_service.create_organization(db, organization)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/", response_model=list[OrganizationResponse])
def read_all_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return organization_service.list_organizations(db, skip=skip, limit=limit)


@router.get("/public-id/{public_id}", response_model=OrganizationResponse)
def read_organization_by_public_id(
    public_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization = organization_service.get_organization_by_public_id(db, str(public_id))
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.get("/code/{org_code}", response_model=OrganizationResponse)
def read_organization_by_org_code(
    org_code: str = Path(..., min_length=1, max_length=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization = organization_service.get_organization_by_org_code(db, org_code)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.get("/{organization_id}", response_model=OrganizationResponse)
def read_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization = organization_service.get_organization_by_id(db, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_existing_organization(
    organization_id: int,
    organization: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    try:
        updated = organization_service.update_organization(
            db, organization_id, organization
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return updated


@router.delete("/{organization_id}")
def delete_existing_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    try:
        deleted = organization_service.delete_organization(db, organization_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if deleted is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {"message": "Organization deleted successfully"}