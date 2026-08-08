from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.warehouse_match import WarehouseMatch
from app.repositories.base import BaseRepository


class WarehouseMatchRepository(BaseRepository[WarehouseMatch]):
    def __init__(self) -> None:
        super().__init__(model=WarehouseMatch)

    def get_matches_for_lead(
        self,
        db: Session,
        lead_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WarehouseMatch]:
        stmt = (
            select(self.model)
            .where(self.model.lead_id == lead_id)
            .order_by(self.model.match_score.desc())
            .offset(offset)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_matches_for_warehouse(
        self,
        db: Session,
        warehouse_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WarehouseMatch]:
        stmt = (
            select(self.model)
            .where(self.model.warehouse_id == warehouse_id)
            .order_by(self.model.match_score.desc())
            .offset(offset)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_matches_for_requirement(
        self,
        db: Session,
        requirement_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WarehouseMatch]:
        stmt = (
            select(self.model)
            .where(self.model.requirement_id == requirement_id)
            .order_by(self.model.match_score.desc())
            .offset(offset)
            .limit(limit)
        )
        return db.execute(stmt).scalars().all()

    def get_by_lead_and_warehouse(
        self,
        db: Session,
        lead_id: int,
        warehouse_id: int,
    ) -> Optional[WarehouseMatch]:
        stmt = select(self.model).where(
            self.model.lead_id == lead_id,
            self.model.warehouse_id == warehouse_id,
        )
        return db.execute(stmt).scalars().first()