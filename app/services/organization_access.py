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


def require_record_access(db: Session, user: User, record, organization_id: int | None = None):
    """Authorize a record after its owning organization has been resolved.

    Legacy entities do not all carry an organization_id column.  Callers must
    resolve ownership through the canonical relationship and pass that value;
    this helper keeps the response and global-admin policy consistent.
    """
    resolved_id = organization_id if organization_id is not None else getattr(record, "organization_id", None)
    if resolved_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization ownership is required")
    require_organization_access(db, user, resolved_id)
    return record


def organization_for_company(db: Session, company_id: int) -> int | None:
    from app.models.company import Company
    company = db.get(Company, company_id)
    return company.organization_id if company is not None else None


def organization_for_lead(db: Session, lead_id: int) -> int | None:
    from app.models.company import Company
    from app.models.lead import Lead
    return db.query(Company.organization_id).join(Lead, Lead.company_id == Company.id).filter(Lead.id == lead_id).scalar()


def organization_for_requirement(db: Session, requirement_id: int) -> int | None:
    from app.models.company import Company
    from app.models.lead import Lead
    from app.models.requirement import Requirement
    return (db.query(Company.organization_id)
            .join(Lead, Lead.company_id == Company.id)
            .join(Requirement, Requirement.lead_id == Lead.id)
            .filter(Requirement.id == requirement_id).scalar())


def organization_for_match(db: Session, match_id: int) -> int | None:
    from app.models.company import Company
    from app.models.lead import Lead
    from app.models.warehouse_match import WarehouseMatch
    return (db.query(Company.organization_id)
            .join(Lead, Lead.company_id == Company.id)
            .join(WarehouseMatch, WarehouseMatch.lead_id == Lead.id)
            .filter(WarehouseMatch.id == match_id).scalar())


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