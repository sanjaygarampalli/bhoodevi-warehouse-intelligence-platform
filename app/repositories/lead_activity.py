from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lead_activity import LeadActivity
from app.repositories.base import BaseRepository


class LeadActivityRepository(BaseRepository[LeadActivity]):
    def __init__(self) -> None:
        super().__init__(model=LeadActivity)

    def get_by_lead_id(
        self,
        db: Session,
        lead_id: int,
    ) -> List[LeadActivity]:
        stmt = (
            select(self.model)
            .where(self.model.lead_id == lead_id)
            .order_by(self.model.activity_date.desc())
        )
        return db.execute(stmt).scalars().all()