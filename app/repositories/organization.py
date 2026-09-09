from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.organization import Organization
from app.repositories.base import BaseRepository


class OrganizationRepository(BaseRepository[Organization]):
    def __init__(self) -> None:
        super().__init__(model=Organization)

    def get_by_org_code(self, db: Session, org_code: str) -> Organization | None:
        stmt = select(self.model).where(self.model.org_code == org_code)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_public_id(self, db: Session, public_id: str) -> Organization | None:
        stmt = select(self.model).where(self.model.public_id == public_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> list[Organization]:
        stmt = select(self.model).order_by(self.model.id).offset(skip).limit(limit)
        return db.execute(stmt).scalars().all()

    def get_by_gstin(self, db: Session, gstin: str) -> Organization | None:
        stmt = select(self.model).where(self.model.gstin == gstin)
        return db.execute(stmt).scalar_one_or_none()

    def get_by_pan(self, db: Session, pan: str) -> Organization | None:
        stmt = select(self.model).where(self.model.pan == pan)
        return db.execute(stmt).scalar_one_or_none()

    def has_companies(self, db: Session, organization_id: int) -> bool:
        stmt = select(Company.id).where(
            Company.organization_id == organization_id
        ).limit(1)
        return db.execute(stmt).first() is not None