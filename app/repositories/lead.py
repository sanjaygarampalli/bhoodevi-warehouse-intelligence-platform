from typing import Iterator, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, raiseload, selectinload

from app.models.company import Company
from app.models.lead import Lead, LeadStatus
from app.models.requirement import Requirement, RequirementStatus
from app.models.warehouse_match import WarehouseMatch
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository[Lead]):
    def __init__(self) -> None:
        super().__init__(model=Lead)

    @staticmethod
    def _intelligence_options():
        return (
            joinedload(Lead.company).joinedload(Company.organization_owners),
            joinedload(Lead.company).selectinload(Company.decision_makers),
            selectinload(Lead.requirements),
            selectinload(Lead.activities),
            selectinload(Lead.warehouse_matches).joinedload(WarehouseMatch.warehouse),
            raiseload("*"),
        )

    def get_for_intelligence(self, db: Session, lead_id: int) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id).options(*self._intelligence_options())
        return db.scalars(stmt).one_or_none()

    def iter_for_intelligence(
        self, db: Session, *, industry: str | None = None,
        organization_id: int | None = None, has_active_requirement: bool | None = None,
        status: LeadStatus | None = None, batch_size: int = 100,
    ) -> Iterator[Lead]:
        """Keyset batches with shared eager loading, not one query per prospect."""
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        stmt = select(Lead)
        if industry is not None:
            stmt = stmt.where(Lead.company.has(Company.industry == industry))
        if organization_id is not None:
            stmt = stmt.where(Lead.company.has(Company.organization_id == organization_id))
        if has_active_requirement is not None:
            active = Lead.requirements.any(Requirement.requirement_status == RequirementStatus.ACTIVE)
            stmt = stmt.where(active if has_active_requirement else ~active)
        if status is not None:
            stmt = stmt.where(Lead.status == status)
        else:
            stmt = stmt.where(Lead.status.not_in((LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED)))
        last_id = None
        while True:
            batch_stmt = stmt if last_id is None else stmt.where(Lead.id > last_id)
            batch = list(db.scalars(batch_stmt.order_by(Lead.id).limit(batch_size)
                                   .options(*self._intelligence_options())))
            if not batch:
                break
            yield from batch
            last_id = batch[-1].id
            if len(batch) < batch_size:
                break

    def get_by_company_id(
        self,
        db: Session,
        company_id: int,
    ) -> List[Lead]:
        stmt = select(self.model).where(
            self.model.company_id == company_id
        )
        return db.execute(stmt).scalars().all()