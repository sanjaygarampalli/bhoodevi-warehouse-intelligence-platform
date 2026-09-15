from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.repositories.warehouse_pilot_assessment import WarehousePilotAssessmentRepository
from app.schemas.warehouse_pilot_assessment import (
    WarehousePilotAssessmentCreateRequest,
    WarehousePilotAssessmentResponse,
    WarehousePilotAssessmentResult,
)
from app.services.organization_access import require_organization_access, require_organization_write
from app.services.warehouse_pilot_assessment_persistence import (
    WarehousePilotAssessmentPersistenceError,
    WarehousePilotAssessmentPersistenceService,
)
from app.models.company import Company
from app.models.warehouse import Warehouse

router = APIRouter(tags=["Warehouse Pilot"])
service = WarehousePilotAssessmentPersistenceService()
repository = WarehousePilotAssessmentRepository()


@router.post("/warehouse-pilot-assessments/evaluate-and-persist", response_model=WarehousePilotAssessmentResult, status_code=status.HTTP_201_CREATED)
def evaluate_and_persist(data: WarehousePilotAssessmentCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    warehouse = db.get(Warehouse, data.warehouse_id)
    company = db.get(Company, data.company_id)
    if warehouse is None or company is None:
        raise HTTPException(status_code=404, detail="Warehouse or company not found")
    if warehouse.organization_id != company.organization_id:
        raise HTTPException(status_code=403, detail="Warehouse and company must belong to the same organization")
    require_organization_write(db, user, warehouse.organization_id)
    try:
        assessment = service.assess_and_persist(db, data, user_id=user.id, organization_id=warehouse.organization_id)
        return WarehousePilotAssessmentResult(assessment=assessment)
    except WarehousePilotAssessmentPersistenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/warehouse-pilot-assessments/{assessment_id}", response_model=WarehousePilotAssessmentResponse)
def get_assessment(assessment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assessment = repository.get_by_id(db, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Warehouse Pilot assessment not found")
    require_organization_access(db, user, assessment.organization_id)
    return assessment