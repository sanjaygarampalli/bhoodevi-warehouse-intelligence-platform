from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.warehouse_pilot_assessment import WarehousePilotAssessment


class WarehousePilotAssessmentRepository:
    def create(self, db: Session, assessment: WarehousePilotAssessment):
        db.add(assessment)
        db.flush()
        return assessment

    def get_by_id(self, db: Session, assessment_id: int):
        return db.scalar(select(WarehousePilotAssessment).where(WarehousePilotAssessment.id == assessment_id))

    def list_for_company(self, db: Session, company_id: int, organization_id: int):
        return list(db.scalars(select(WarehousePilotAssessment).where(
            WarehousePilotAssessment.company_id == company_id,
            WarehousePilotAssessment.organization_id == organization_id,
        ).order_by(WarehousePilotAssessment.assessed_at.desc())))

    def list_for_warehouse(self, db: Session, warehouse_id: int, organization_id: int):
        return list(db.scalars(select(WarehousePilotAssessment).where(
            WarehousePilotAssessment.warehouse_id == warehouse_id,
            WarehousePilotAssessment.organization_id == organization_id,
        ).order_by(WarehousePilotAssessment.assessed_at.desc())))