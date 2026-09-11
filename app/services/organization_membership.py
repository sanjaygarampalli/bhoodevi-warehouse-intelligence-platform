from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.organization_membership import MembershipStatus, OrganizationMembership
from app.models.user import User
from app.schemas.organization_membership import OrganizationMembershipCreate, OrganizationMembershipUpdate


class OrganizationMembershipService:
    def list_members(self, db: Session, organization_id: int):
        return list(db.scalars(select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id
        ).order_by(OrganizationMembership.id)).all())

    def get_member(self, db: Session, organization_id: int, membership_id: int):
        return db.scalar(select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.id == membership_id,
        ))

    def create_member(self, db: Session, organization_id: int, data: OrganizationMembershipCreate):
        if db.get(Organization, organization_id) is None:
            raise LookupError("Organization not found")
        if db.get(User, data.user_id) is None:
            raise LookupError("User not found")
        membership = OrganizationMembership(organization_id=organization_id, **data.model_dump())
        db.add(membership)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("User already belongs to this organization") from exc
        db.refresh(membership)
        return membership

    def update_member(self, db: Session, membership: OrganizationMembership, data: OrganizationMembershipUpdate):
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(membership, key, value)
        db.commit()
        db.refresh(membership)
        return membership

    def deactivate_member(self, db: Session, membership: OrganizationMembership):
        membership.status = MembershipStatus.INACTIVE
        db.commit()
        db.refresh(membership)
        return membership