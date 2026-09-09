from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.deal_pipeline_stage import DealPipelineStage
from app.models.deal_stage_history import DealStageHistory
from app.repositories.base import BaseRepository


class DealPipelineStageRepository(BaseRepository[DealPipelineStage]):
    def __init__(self):
        super().__init__(DealPipelineStage)

    def get_locked(self, db: Session, stage_id: int):
        return db.scalar(select(DealPipelineStage).where(DealPipelineStage.id == stage_id)
                         .with_for_update().execution_options(populate_existing=True))

    def list_stages(self, db: Session, organization_id=None, is_active=None, skip=0, limit=100):
        stmt = select(DealPipelineStage)
        if organization_id is not None:
            stmt = stmt.where(DealPipelineStage.organization_id == organization_id)
        if is_active is not None:
            stmt = stmt.where(DealPipelineStage.is_active == is_active)
        return list(db.scalars(stmt.order_by(DealPipelineStage.organization_id,
                                            DealPipelineStage.stage_order, DealPipelineStage.id)
                               .offset(skip).limit(limit)))

    def is_referenced(self, db: Session, stage_id: int) -> bool:
        return (db.scalar(select(Deal.id).where(Deal.stage_id == stage_id).limit(1)) is not None
                or db.scalar(select(DealStageHistory.id).where(or_(
                    DealStageHistory.from_stage_id == stage_id,
                    DealStageHistory.to_stage_id == stage_id,
                )).limit(1)) is not None)