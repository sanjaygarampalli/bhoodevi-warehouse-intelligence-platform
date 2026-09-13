from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.company import Company
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.warehouse_pilot import (
    CommercialProfileResponse, CommercialProfileWrite, OperationalProfileResponse,
    OperationalProfileWrite, PilotAssessmentRequest, PilotAssessmentResponse,
    RequirementAssessmentResponse, RequirementAssessmentWrite,
)
from app.services.organization_access import require_organization_access, require_organization_write
from app.services.warehouse_pilot_assessment import WarehousePilotService

router = APIRouter(tags=["Warehouse Pilot"])
service = WarehousePilotService()


def warehouse_org(db, warehouse_id):
    item = db.get(Warehouse, warehouse_id)
    if item is None or item.organization_id is None: raise HTTPException(404, "Warehouse not found")
    return item.organization_id


def company_org(db, company_id):
    item = db.get(Company, company_id)
    if item is None: raise HTTPException(404, "Company not found")
    return item.organization_id


def values(data):
    return data.model_dump(exclude_unset=True, mode="python")


@router.get("/warehouses/{warehouse_id}/operational-profile", response_model=OperationalProfileResponse)
def get_operational_profile(warehouse_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_access(db, user, organization_id)
    profile = service.get_operational(db, warehouse_id, organization_id)
    if profile is None: raise HTTPException(404, "Operational profile not found")
    return profile


@router.post("/warehouses/{warehouse_id}/operational-profile", response_model=OperationalProfileResponse, status_code=status.HTTP_201_CREATED)
def create_operational_profile(warehouse_id: int, data: OperationalProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_write(db, user, organization_id)
    try: return service.save_operational(db, warehouse_id, organization_id, values(data), True)
    except Exception as exc: raise HTTPException(409, str(exc)) from exc


@router.patch("/warehouses/{warehouse_id}/operational-profile", response_model=OperationalProfileResponse)
def update_operational_profile(warehouse_id: int, data: OperationalProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_write(db, user, organization_id)
    profile = service.save_operational(db, warehouse_id, organization_id, values(data))
    if profile is None: raise HTTPException(404, "Operational profile not found")
    return profile


@router.get("/warehouses/{warehouse_id}/commercial-profile", response_model=CommercialProfileResponse)
def get_commercial_profile(warehouse_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_access(db, user, organization_id)
    profile = service.get_commercial(db, warehouse_id, organization_id)
    if profile is None: raise HTTPException(404, "Commercial profile not found")
    return profile


@router.post("/warehouses/{warehouse_id}/commercial-profile", response_model=CommercialProfileResponse, status_code=status.HTTP_201_CREATED)
def create_commercial_profile(warehouse_id: int, data: CommercialProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_write(db, user, organization_id)
    return service.save_commercial(db, warehouse_id, organization_id, values(data), True)


@router.patch("/warehouses/{warehouse_id}/commercial-profile", response_model=CommercialProfileResponse)
def update_commercial_profile(warehouse_id: int, data: CommercialProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_write(db, user, organization_id)
    profile = service.save_commercial(db, warehouse_id, organization_id, values(data))
    if profile is None: raise HTTPException(404, "Commercial profile not found")
    return profile


@router.get("/companies/{company_id}/warehouse-requirement-assessment", response_model=RequirementAssessmentResponse)
def get_requirement_assessment(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = company_org(db, company_id); require_organization_access(db, user, organization_id)
    item = service.get_requirement_assessment(db, company_id, organization_id)
    if item is None: raise HTTPException(404, "Requirement assessment not found")
    return item


@router.post("/companies/{company_id}/warehouse-requirement-assessment", response_model=RequirementAssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_requirement_assessment(company_id: int, data: RequirementAssessmentWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = company_org(db, company_id); require_organization_write(db, user, organization_id)
    return service.save_requirement_assessment(db, company_id, organization_id, values(data), True)


@router.patch("/companies/{company_id}/warehouse-requirement-assessment", response_model=RequirementAssessmentResponse)
def update_requirement_assessment(company_id: int, data: RequirementAssessmentWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = company_org(db, company_id); require_organization_write(db, user, organization_id)
    item = service.save_requirement_assessment(db, company_id, organization_id, values(data))
    if item is None: raise HTTPException(404, "Requirement assessment not found")
    return item


@router.post("/warehouse-pilot-assessments/evaluate", response_model=PilotAssessmentResponse)
def evaluate_pilot(data: PilotAssessmentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    warehouse_organization = warehouse_org(db, data.warehouse_id)
    company_organization = company_org(db, data.company_id)
    if warehouse_organization != company_organization: raise HTTPException(403, "Warehouse and company must belong to the same organization")
    require_organization_access(db, user, warehouse_organization)
    return service.evaluate(db, data.warehouse_id, data.company_id, warehouse_organization)