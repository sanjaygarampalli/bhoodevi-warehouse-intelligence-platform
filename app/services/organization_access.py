from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.organization_membership import (
    MembershipStatus,
    OrganizationMemberRole,
    OrganizationMembership,
)
from app.models.user import User

ADMIN_ROLES = {OrganizationMemberRole.OWNER, OrganizationMemberRole.ADMIN}
WRITE_ROLES = ADMIN_ROLES | {OrganizationMemberRole.MANAGER, OrganizationMemberRole.MEMBER}


def is_global_admin(user: User) -> bool:
    return user.role == "admin"


def get_active_membership(db: Session, user_id: int, organization_id: int):
    return db.scalar(select(OrganizationMembership).where(
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.status == MembershipStatus.ACTIVE,
    ))


def require_organization_access(db: Session, user: User, organization_id: int):
    if is_global_admin(user):
        return None
    membership = get_active_membership(db, user.id, organization_id)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active organization membership required")
    return membership


def require_organization_write(db: Session, user: User, organization_id: int):
    membership = require_organization_access(db, user, organization_id)
    if membership is not None and membership.role not in WRITE_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization write access required")
    return membership


def require_organization_admin(db: Session, user: User, organization_id: int):
    membership = require_organization_access(db, user, organization_id)
    if membership is not None and membership.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization administration access required")
    return membership


def organization_reader(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    require_organization_access(db, current_user, organization_id)
    return current_user


def organization_writer(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    require_organization_write(db, current_user, organization_id)
    return current_user


def organization_admin(
    organization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    require_organization_admin(db, current_user, organization_id)
    return current_user