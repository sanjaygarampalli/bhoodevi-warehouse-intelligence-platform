from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.organization_membership import (
    OrganizationMembershipCreate, OrganizationMembershipResponse, OrganizationMembershipUpdate,
)
from app.services.organization_access import require_organization_admin
from app.services.organization_membership import OrganizationMembershipService

router = APIRouter(prefix="/organizations/{organization_id}/members", tags=["Organization Memberships"])
service = OrganizationMembershipService()


def admin_context(organization_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_organization_admin(db, current_user, organization_id)
    return current_user


@router.get("", response_model=list[OrganizationMembershipResponse])
def list_members(organization_id: int, db: Session = Depends(get_db), _: User = Depends(admin_context)):
    return service.list_members(db, organization_id)


@router.get("/{membership_id}", response_model=OrganizationMembershipResponse)
def get_member(organization_id: int, membership_id: int, db: Session = Depends(get_db), _: User = Depends(admin_context)):
    membership = service.get_member(db, organization_id, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return membership


@router.post("", response_model=OrganizationMembershipResponse, status_code=status.HTTP_201_CREATED)
def create_member(organization_id: int, data: OrganizationMembershipCreate, db: Session = Depends(get_db), _: User = Depends(admin_context)):
    try:
        return service.create_member(db, organization_id, data)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{membership_id}", response_model=OrganizationMembershipResponse)
def update_member(organization_id: int, membership_id: int, data: OrganizationMembershipUpdate, db: Session = Depends(get_db), _: User = Depends(admin_context)):
    membership = service.get_member(db, organization_id, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return service.update_member(db, membership, data)


@router.delete("/{membership_id}", response_model=OrganizationMembershipResponse)
def deactivate_member(organization_id: int, membership_id: int, db: Session = Depends(get_db), _: User = Depends(admin_context)):
    membership = service.get_member(db, organization_id, membership_id)
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")
    return service.deactivate_member(db, membership)