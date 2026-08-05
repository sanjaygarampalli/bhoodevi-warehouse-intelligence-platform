from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self) -> None:
        super().__init__(model=Lead)

    def get_by_company_id(
        self,
        db: Session,
        company_id: int,
    ) -> List[Lead]:
        stmt = select(self.model).where(
            self.model.company_id == company_id
        )
        return db.execute(stmt).scalars().all()