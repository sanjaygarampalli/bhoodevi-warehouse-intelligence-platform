from typing import List, Optional

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.models.decision_maker import DecisionMaker
from app.repositories.base import BaseRepository


class DecisionMakerRepository(BaseRepository[DecisionMaker]):
    def __init__(self) -> None:
        super().__init__(model=DecisionMaker)

    def get_by_company_id(
        self,
        db: Session,
        company_id: int,
    ) -> List[DecisionMaker]:
        stmt = select(self.model).where(
            self.model.company_id == company_id
        )
        return db.execute(stmt).scalars().all()