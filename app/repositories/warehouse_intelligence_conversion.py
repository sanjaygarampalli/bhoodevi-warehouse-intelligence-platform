from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.warehouse_intelligence_conversion import WarehouseIntelligenceOpportunityConversion


class WarehouseIntelligenceOpportunityConversionRepository:
    def get_by_id(self, db: Session, conversion_id: int, *, lock=False):
        stmt = select(WarehouseIntelligenceOpportunityConversion).where(
            WarehouseIntelligenceOpportunityConversion.id == conversion_id,
        ).options(joinedload(WarehouseIntelligenceOpportunityConversion.deal))
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return db.scalar(stmt)

    def get_by_source(self, db: Session, warehouse_match_id: int, *, lock=False):
        stmt = select(WarehouseIntelligenceOpportunityConversion).where(
            WarehouseIntelligenceOpportunityConversion.warehouse_match_id == warehouse_match_id,
        ).options(joinedload(WarehouseIntelligenceOpportunityConversion.deal))
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return db.scalar(stmt)

    def get_by_deal(self, db: Session, deal_id: int):
        return db.scalar(select(WarehouseIntelligenceOpportunityConversion).where(
            WarehouseIntelligenceOpportunityConversion.deal_id == deal_id,
        ))

    def create_pending(self, db: Session, conversion):
        db.add(conversion)
        db.flush()
        return conversion