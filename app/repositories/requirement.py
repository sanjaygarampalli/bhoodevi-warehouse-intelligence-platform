from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement import Requirement
from app.repositories.base import BaseRepository


class RequirementRepository(BaseRepository[Requirement]):
    def __init__(self) -> None:
        super().__init__(model=Requirement)

    def get_by_lead_id(
        self,
        db: Session,
        lead_id: int,
    ) -> List[Requirement]:
        stmt = (
            select(self.model)
            .where(self.model.lead_id == lead_id)
            .order_by(self.model.created_at.desc())
        )
        return db.execute(stmt).scalars().all()