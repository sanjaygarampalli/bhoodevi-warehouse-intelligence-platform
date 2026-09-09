from typing import Iterator, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, raiseload

from app.models.warehouse_match import WarehouseMatch, WarehouseMatchStatus
from app.models.warehouse import AvailabilityStatus, Warehouse
from app.models.requirement import Requirement
from app.repositories.base import BaseRepository


class WarehouseMatchRepository(BaseRepository[WarehouseMatch]):
    def __init__(self) -> None:
        super().__init__(model=WarehouseMatch)

    def lock_requirement(self, db: Session, requirement_id: int) -> Requirement | None:
        return db.scalar(select(Requirement).where(Requirement.id == requirement_id)
                         .with_for_update().execution_options(populate_existing=True))

    def get_generation_matches(self, db: Session, requirement_id: int) -> list[WarehouseMatch]:
        return list(db.scalars(select(self.model)
                    .where(self.model.requirement_id == requirement_id)
                    .order_by(self.model.warehouse_id).with_for_update()
                    .execution_options(populate_existing=True)))

    def get_generation_warehouses(
        self, db: Session, requirement_id: int, *,
        eligible_statuses: tuple[AvailabilityStatus, ...],
    ) -> list[Warehouse]:
        existing = select(self.model.warehouse_id).where(self.model.requirement_id == requirement_id)
        return list(db.scalars(select(Warehouse).where(
            Warehouse.availability_status.in_(eligible_statuses) | Warehouse.id.in_(existing)
        ).order_by(Warehouse.id).options(raiseload("*"))
          .execution_options(populate_existing=True)))

    def iter_recommendation_candidates(
        self, db: Session, requirement_id: int, *,
        eligible_statuses: tuple[AvailabilityStatus, ...], batch_size: int,
    ) -> Iterator[tuple[Warehouse, int | None, WarehouseMatchStatus | None]]:
        """Stream eligible stock with its existing workflow identity, without N+1."""
        stmt = (
            select(Warehouse, WarehouseMatch.id, WarehouseMatch.status)
            .outerjoin(WarehouseMatch, (
                (WarehouseMatch.warehouse_id == Warehouse.id)
                & (WarehouseMatch.requirement_id == requirement_id)
            ))
            .where(Warehouse.availability_status.in_(eligible_statuses))
            .order_by(Warehouse.id)
            .options(raiseload("*"))
            .execution_options(yield_per=batch_size)
        )
        result = db.execute(stmt)
        try:
            for warehouse, match_id, match_status in result:
                yield warehouse, match_id, match_status
        finally:
            result.close()

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
            .order_by(self.model.match_score.desc(), self.model.warehouse_id, self.model.id)
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
            .order_by(self.model.match_score.desc(), self.model.warehouse_id, self.model.id)
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
            .order_by(self.model.match_score.desc(), self.model.warehouse_id, self.model.id)
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