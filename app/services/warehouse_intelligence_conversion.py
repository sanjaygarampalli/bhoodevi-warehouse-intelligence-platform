from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.warehouse import Warehouse
from app.models.warehouse_match import WarehouseMatch, WarehouseMatchStatus
from app.models.warehouse_intelligence_conversion import (
    WarehouseIntelligenceConversionSource,
    WarehouseIntelligenceConversionStatus,
    WarehouseIntelligenceOpportunityConversion,
)
from app.repositories.warehouse_intelligence_conversion import WarehouseIntelligenceOpportunityConversionRepository
from app.schemas.deal import DealCreate
from app.schemas.warehouse_intelligence_conversion import WarehouseMatchOpportunityConversionRequest
from app.services.deal import DealService
from app.services.deal_workflow import DealConflict


class WarehouseIntelligenceConversionError(ValueError):
    pass


class WarehouseIntelligenceOpportunityConversionService:
    def __init__(self):
        self.repository = WarehouseIntelligenceOpportunityConversionRepository()
        self.deals = DealService()

    def convert_warehouse_match(self, db: Session, warehouse_match_id: int, payload: WarehouseMatchOpportunityConversionRequest, *, user_id: int, organization_id: int):
        match = db.scalar(
            select(WarehouseMatch).where(WarehouseMatch.id == warehouse_match_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        if match is None:
            raise LookupError("Warehouse match not found")
        company = db.get(Company, match.lead.company_id)
        if company is None or company.organization_id != organization_id:
            raise WarehouseIntelligenceConversionError("Warehouse match does not belong to the requested organization")
        warehouse = db.get(Warehouse, match.warehouse_id)
        if warehouse is None or warehouse.organization_id != organization_id:
            raise WarehouseIntelligenceConversionError("Warehouse match warehouse does not belong to the requested organization")
        existing = self.repository.get_by_source(db, match.id, lock=True)
        if existing is not None:
            if existing.status == WarehouseIntelligenceConversionStatus.CONVERTED and existing.deal is not None:
                return existing, existing.deal, False
            raise WarehouseIntelligenceConversionError("Warehouse match already has a conversion in progress or failed")

        if match.status in (WarehouseMatchStatus.REJECTED, WarehouseMatchStatus.STALE, WarehouseMatchStatus.CONVERTED):
            raise WarehouseIntelligenceConversionError("Warehouse match is not eligible for conversion")

        conversion = WarehouseIntelligenceOpportunityConversion(
            organization_id=organization_id,
            source_type=WarehouseIntelligenceConversionSource.WAREHOUSE_MATCH,
            warehouse_match_id=match.id,
            status=WarehouseIntelligenceConversionStatus.PENDING,
            created_by_user_id=user_id,
        )
        try:
            self.repository.create_pending(db, conversion)
            deal = self.deals.create_deal_in_transaction(
                db,
                DealCreate(
                    deal_name=payload.deal_name,
                    lead_id=match.lead_id,
                    requirement_id=payload.requirement_id,
                    selected_warehouse_match_id=match.id,
                    stage_id=payload.stage_id,
                    expected_revenue=payload.expected_revenue,
                    currency=payload.currency,
                    expected_close_date=payload.expected_close_date,
                    notes=payload.notes,
                ),
                changed_by_user_id=user_id,
            )
            conversion.deal_id = deal.id
            conversion.status = WarehouseIntelligenceConversionStatus.CONVERTED
            conversion.converted_at = datetime.now(timezone.utc)
            match.status = WarehouseMatchStatus.CONVERTED
            db.commit()
            db.refresh(conversion)
            db.refresh(deal)
            return conversion, deal, True
        except Exception as exc:
            db.rollback()
            if isinstance(exc, WarehouseIntelligenceConversionError):
                raise
            if isinstance(exc, (DealConflict, LookupError)):
                raise
            raise WarehouseIntelligenceConversionError("Warehouse intelligence conversion failed") from exc