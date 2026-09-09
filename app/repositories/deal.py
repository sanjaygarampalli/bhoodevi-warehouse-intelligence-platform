from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.deal import Deal
from app.models.deal_stage_history import DealStageHistory
from app.models.lead import Lead
from app.models.warehouse_match import WarehouseMatch


class DealRepository:
    def get_by_id(self, db: Session, deal_id: int, *, lock=False):
        stmt = select(Deal).where(Deal.id == deal_id)
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        else:
            stmt = stmt.options(joinedload(Deal.stage))
        return db.scalar(stmt)

    def get_reference(self, db: Session, model, reference_id: int):
        return db.scalar(select(model).where(model.id == reference_id).with_for_update()
                         .execution_options(populate_existing=True))

    def list_deals(self, db: Session, *, stage_id=None, lead_id=None, organization_id=None,
                   is_active=None, skip=0, limit=100):
        stmt = select(Deal).options(joinedload(Deal.stage))
        for field, value in ((Deal.stage_id, stage_id), (Deal.lead_id, lead_id),
                             (Deal.organization_id, organization_id)):
            if value is not None:
                stmt = stmt.where(field == value)
        if is_active is not None:
            stmt = stmt.where(Deal.deal_status == "OPEN" if is_active else Deal.deal_status != "OPEN")
        return list(db.scalars(stmt.order_by(Deal.created_at.desc(), Deal.id.desc()).offset(skip).limit(limit)))

    def history(self, db: Session, deal_id: int, skip=0, limit=100):
        return list(db.scalars(select(DealStageHistory).where(DealStageHistory.deal_id == deal_id)
                               .order_by(DealStageHistory.changed_at.desc(), DealStageHistory.id.desc())
                               .offset(skip).limit(limit)))

    def save(self, db: Session, deal: Deal, history: DealStageHistory | None = None):
        db.add(deal)
        db.flush()
        if history is not None:
            history.deal_id = deal.id
            db.add(history)
        db.commit()
        return self.get_by_id(db, deal.id)

    def has_reference(self, db: Session, entity: str, entity_id: int) -> bool:
        stmt = select(Deal.id)
        if entity == "lead":
            stmt = stmt.where(Deal.lead_id == entity_id)
        elif entity == "requirement":
            stmt = stmt.where(Deal.requirement_id == entity_id)
        elif entity == "match":
            stmt = stmt.where(Deal.selected_warehouse_match_id == entity_id)
        elif entity == "warehouse":
            stmt = stmt.join(WarehouseMatch, Deal.selected_warehouse_match_id == WarehouseMatch.id)
            stmt = stmt.where(WarehouseMatch.warehouse_id == entity_id)
        elif entity == "company":
            stmt = stmt.join(Lead, Deal.lead_id == Lead.id).where(Lead.company_id == entity_id)
        else:
            raise ValueError("Unknown Deal reference type")
        return db.scalar(stmt.limit(1)) is not None