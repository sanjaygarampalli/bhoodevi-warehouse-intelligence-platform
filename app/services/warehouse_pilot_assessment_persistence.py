from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.warehouse import Warehouse
from app.models.warehouse_capability import WarehouseCapabilityProfile
from app.models.warehouse_pilot import WarehouseCommercialProfile, WarehouseOperationalProfile, WarehouseRequirementAssessment
from app.models.warehouse_pilot_assessment import WarehousePilotAssessment
from app.models.warehouse_requirement import CompanyWarehouseRequirementProfile
from app.repositories.warehouse_pilot_assessment import WarehousePilotAssessmentRepository
from app.services.warehouse_pilot_assessment import WarehousePilotService


class WarehousePilotAssessmentPersistenceError(ValueError):
    pass


class WarehousePilotAssessmentPersistenceService:
    evaluation_version = "v1"

    def __init__(self):
        self.repository = WarehousePilotAssessmentRepository()
        self.evaluator = WarehousePilotService()

    @staticmethod
    def _jsonable(value: Any):
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, dict):
            return {str(key): WarehousePilotAssessmentPersistenceService._jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [WarehousePilotAssessmentPersistenceService._jsonable(item) for item in value]
        return value

    @classmethod
    def _row_snapshot(cls, row: Any) -> dict[str, Any] | None:
        if row is None:
            return None
        return cls._jsonable({column.key: getattr(row, column.key) for column in inspect(row).mapper.column_attrs})

    def assess_and_persist(self, db: Session, payload, *, user_id: int, organization_id: int):
        warehouse = db.scalar(select(Warehouse).where(Warehouse.id == payload.warehouse_id))
        company = db.scalar(select(Company).where(Company.id == payload.company_id))
        if warehouse is None or warehouse.organization_id != organization_id:
            raise WarehousePilotAssessmentPersistenceError("Warehouse does not belong to the requested organization")
        if company is None or company.organization_id != organization_id:
            raise WarehousePilotAssessmentPersistenceError("Company does not belong to the requested organization")

        result = self.evaluator.evaluate(db, warehouse.id, company.id, organization_id)
        if not isinstance(result, dict) or result.get("overall_classification") is None:
            raise WarehousePilotAssessmentPersistenceError("Warehouse Pilot evaluator returned an invalid result")

        capability = db.scalar(select(WarehouseCapabilityProfile).where(WarehouseCapabilityProfile.warehouse_id == warehouse.id, WarehouseCapabilityProfile.organization_id == organization_id))
        company_requirement = db.scalar(select(CompanyWarehouseRequirementProfile).where(CompanyWarehouseRequirementProfile.company_id == company.id, CompanyWarehouseRequirementProfile.organization_id == organization_id))
        operational = db.scalar(select(WarehouseOperationalProfile).where(WarehouseOperationalProfile.warehouse_id == warehouse.id, WarehouseOperationalProfile.organization_id == organization_id))
        commercial = db.scalar(select(WarehouseCommercialProfile).where(WarehouseCommercialProfile.warehouse_id == warehouse.id, WarehouseCommercialProfile.organization_id == organization_id))
        requirement = db.scalar(select(WarehouseRequirementAssessment).where(WarehouseRequirementAssessment.company_id == company.id, WarehouseRequirementAssessment.organization_id == organization_id))

        assessment = WarehousePilotAssessment(
            organization_id=organization_id,
            company_id=company.id,
            warehouse_id=warehouse.id,
            assessed_by_user_id=user_id,
            capability_profile_id=capability.id if capability else None,
            company_requirement_profile_id=company_requirement.id if company_requirement else None,
            operational_profile_id=operational.id if operational else None,
            commercial_profile_id=commercial.id if commercial else None,
            requirement_assessment_id=requirement.id if requirement else None,
            evaluation_version=self.evaluation_version,
            overall_classification=result["overall_classification"],
            result_snapshot=self._jsonable(result),
            source_snapshot={
                "warehouse": self._row_snapshot(warehouse),
                "company": self._row_snapshot(company),
                "warehouse_capability_profile": self._row_snapshot(capability),
                "company_warehouse_requirement_profile": self._row_snapshot(company_requirement),
                "warehouse_operational_profile": self._row_snapshot(operational),
                "warehouse_commercial_profile": self._row_snapshot(commercial),
                "warehouse_requirement_assessment": self._row_snapshot(requirement),
            },
        )
        try:
            self.repository.create(db, assessment)
            db.commit()
            db.refresh(assessment)
            return assessment
        except Exception as exc:
            db.rollback()
            raise WarehousePilotAssessmentPersistenceError("Warehouse Pilot assessment persistence failed") from exc