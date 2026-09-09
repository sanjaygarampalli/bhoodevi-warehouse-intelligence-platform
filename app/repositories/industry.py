from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.industry import Industry
from app.models.organization import Organization
from app.repositories.base import BaseRepository


class IndustryRepository(BaseRepository[Industry]):
    def __init__(self) -> None:
        super().__init__(model=Industry)

    def get_by_code(self, db: Session, code: str) -> Industry | None:
        stmt = select(self.model).where(self.model.code == code)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Industry]:
        stmt = select(self.model).order_by(self.model.id).offset(skip).limit(limit)
        return db.execute(stmt).scalars().all()

    def get_by_name(self, db: Session, name: str) -> Industry | None:
        stmt = select(self.model).where(self.model.name == name)
        return db.execute(stmt).scalar_one_or_none()

    def delete(self, db: Session, obj: Industry) -> None:
        # Preserve organizations even on databases whose industry FK is restrictive.
        stmt = update(Organization).where(Organization.industry_id == obj.id).values(
            industry_id=None
        )
        db.execute(stmt)
        super().delete(db, obj)