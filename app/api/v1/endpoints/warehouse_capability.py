from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.warehouse_capability import CapabilityProfileResponse, CapabilityProfileWrite
from app.schemas.warehouse_requirement import RequirementProfileResponse, RequirementProfileWrite
from app.schemas.warehouse_evaluation import WarehouseEvaluationRequest, WarehouseEvaluationResponse
from app.services.organization_access import require_organization_access, require_organization_write
from app.services.warehouse_capability_matching import WarehouseCapabilityMatchingService
from app.models.warehouse import Warehouse
from app.models.company import Company

router = APIRouter(tags=["Warehouse Capability Matching"])
service = WarehouseCapabilityMatchingService()


def warehouse_org(db, warehouse_id):
    item = db.get(Warehouse, warehouse_id)
    if item is None or item.organization_id is None:
        raise HTTPException(404, "Warehouse not found")
    return item.organization_id


def company_org(db, company_id):
    item = db.get(Company, company_id)
    if item is None:
        raise HTTPException(404, "Company not found")
    return item.organization_id


@router.get("/warehouses/{warehouse_id}/capability-profile", response_model=CapabilityProfileResponse)
def get_capability_profile(warehouse_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_access(db, user, organization_id)
    profile = service.get_capability(db, warehouse_id, organization_id)
    if profile is None: raise HTTPException(404, "Capability profile not found")
    return profile


@router.post("/warehouses/{warehouse_id}/capability-profile", response_model=CapabilityProfileResponse, status_code=status.HTTP_201_CREATED)
def create_capability_profile(warehouse_id: int, data: CapabilityProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_write(db, user, organization_id)
    return service.save_capability(db, warehouse_id, organization_id, {k: v.model_dump(mode="json") for k, v in data.capabilities.items()}, True)


@router.patch("/warehouses/{warehouse_id}/capability-profile", response_model=CapabilityProfileResponse)
def update_capability_profile(warehouse_id: int, data: CapabilityProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = warehouse_org(db, warehouse_id); require_organization_write(db, user, organization_id)
    profile = service.save_capability(db, warehouse_id, organization_id, {k: v.model_dump(mode="json") for k, v in data.capabilities.items()})
    if profile is None: raise HTTPException(404, "Capability profile not found")
    return profile


@router.get("/companies/{company_id}/warehouse-requirement-profile", response_model=RequirementProfileResponse)
def get_requirement_profile(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = company_org(db, company_id); require_organization_access(db, user, organization_id)
    profile = service.get_requirement(db, company_id, organization_id)
    if profile is None: raise HTTPException(404, "Requirement profile not found")
    return profile


@router.post("/companies/{company_id}/warehouse-requirement-profile", response_model=RequirementProfileResponse, status_code=status.HTTP_201_CREATED)
def create_requirement_profile(company_id: int, data: RequirementProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = company_org(db, company_id); require_organization_write(db, user, organization_id)
    return service.save_requirement(db, company_id, organization_id, {k: v.model_dump(mode="json") for k, v in data.requirements.items()}, True)


@router.patch("/companies/{company_id}/warehouse-requirement-profile", response_model=RequirementProfileResponse)
def update_requirement_profile(company_id: int, data: RequirementProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = company_org(db, company_id); require_organization_write(db, user, organization_id)
    profile = service.save_requirement(db, company_id, organization_id, {k: v.model_dump(mode="json") for k, v in data.requirements.items()})
    if profile is None: raise HTTPException(404, "Requirement profile not found")
    return profile


@router.post("/warehouse-matches/evaluate", response_model=WarehouseEvaluationResponse)
def evaluate_match(data: WarehouseEvaluationRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    warehouse_organization = warehouse_org(db, data.warehouse_id)
    company_organization = company_org(db, data.company_id)
    if warehouse_organization != company_organization:
        raise HTTPException(403, "Warehouse and company must belong to the same organization")
    require_organization_access(db, user, warehouse_organization)
    result = service.evaluate(db, data.warehouse_id, data.company_id, warehouse_organization)
    return result