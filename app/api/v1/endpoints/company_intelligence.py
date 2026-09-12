from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.company_intelligence import CompanyContact, CompanyContactMethod
from app.models.user import User
from app.schemas.company_intelligence import *
from app.services.company_intelligence import *
from app.services.organization_access import require_organization_access, require_organization_write


router = APIRouter(tags=["Company Intelligence"])
service = CompanyIntelligenceService()


def organization_for_company(db: Session, company_id: int) -> int:
    return service.company(db, company_id).organization_id


def contact_or_404(db: Session, contact_id: int):
    contact = db.get(CompanyContact, contact_id)
    if contact is None:
        raise CompanyContactNotFound("Contact not found")
    return contact


def method_or_404(db: Session, method_id: int):
    method = db.get(CompanyContactMethod, method_id)
    if method is None:
        raise CompanyContactMethodNotFound("Contact method not found")
    return method


@router.get("/companies/{company_id}/intelligence")
def intelligence(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_access(db, user, organization_id)
    return service.summary(db, company_id, organization_id)


@router.get("/companies/{company_id}/intelligence-profile", response_model=IntelligenceProfileResponse)
def get_intelligence_profile(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_access(db, user, organization_id)
    profile = service.get_profile(db, company_id, organization_id)
    if profile is None:
        raise CompanyIntelligenceNotFound("Intelligence profile not found")
    return profile


@router.post("/companies/{company_id}/intelligence-profile", response_model=IntelligenceProfileResponse, status_code=status.HTTP_201_CREATED)
def create_intelligence_profile(company_id: int, data: IntelligenceProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.create_profile(db, company_id, organization_id, data)


@router.patch("/companies/{company_id}/intelligence-profile", response_model=IntelligenceProfileResponse)
def update_intelligence_profile(company_id: int, data: IntelligenceProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.update_profile(db, company_id, organization_id, data)


@router.get("/companies/{company_id}/warehouse-profile", response_model=WarehouseProfileResponse)
def get_warehouse_profile(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_access(db, user, organization_id)
    return service.get_warehouse(db, company_id, organization_id)


@router.post("/companies/{company_id}/warehouse-profile", response_model=WarehouseProfileResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse_profile(company_id: int, data: WarehouseProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.save_warehouse(db, company_id, organization_id, data, create=True)


@router.patch("/companies/{company_id}/warehouse-profile", response_model=WarehouseProfileResponse)
def update_warehouse_profile(company_id: int, data: WarehouseProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.save_warehouse(db, company_id, organization_id, data)


@router.get("/companies/{company_id}/contacts", response_model=Page)
def contacts(company_id: int, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_access(db, user, organization_id)
    items, total = service.list_contacts(db, company_id, organization_id, page, page_size)
    return {"items": items, "page": page, "page_size": page_size, "total": total}


@router.post("/companies/{company_id}/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(company_id: int, data: ContactWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.add_contact(db, company_id, organization_id, data)


@router.get("/company-contacts/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contact = contact_or_404(db, contact_id)
    require_organization_access(db, user, contact.organization_id)
    return service.get_contact(db, contact_id, contact.organization_id)


@router.patch("/company-contacts/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, data: ContactUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contact = contact_or_404(db, contact_id)
    require_organization_write(db, user, contact.organization_id)
    return service.update_contact(db, contact_id, contact.organization_id, data)


@router.post("/company-contacts/{contact_id}/methods", response_model=ContactMethodResponse, status_code=status.HTTP_201_CREATED)
def create_method(contact_id: int, data: ContactMethodWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    contact = contact_or_404(db, contact_id)
    require_organization_write(db, user, contact.organization_id)
    return service.add_method(db, contact_id, contact.organization_id, data)


@router.get("/company-contact-methods/{method_id}", response_model=ContactMethodResponse)
def get_method(method_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    method = method_or_404(db, method_id)
    contact = contact_or_404(db, method.contact_id)
    require_organization_access(db, user, contact.organization_id)
    return method


@router.patch("/company-contact-methods/{method_id}", response_model=ContactMethodResponse)
def update_method(method_id: int, data: ContactMethodUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    method = method_or_404(db, method_id)
    contact = contact_or_404(db, method.contact_id)
    require_organization_write(db, user, contact.organization_id)
    return service.update_method(db, method_id, contact.organization_id, data)


@router.get("/companies/{company_id}/icp-assessment", response_model=AssessmentResponse)
def icp(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_access(db, user, organization_id)
    assessment = service.get_icp(db, company_id, organization_id)
    if assessment is None:
        raise CompanyIntelligenceNotFound("ICP assessment not found")
    return assessment


@router.post("/companies/{company_id}/icp-assessment/recalculate", response_model=AssessmentResponse)
def recalculate_icp(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.recalculate_icp(db, company_id, organization_id)


@router.get("/companies/{company_id}/opportunity-assessment", response_model=AssessmentResponse)
def opportunity(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_access(db, user, organization_id)
    assessment = service.get_opportunity(db, company_id, organization_id)
    if assessment is None:
        raise CompanyIntelligenceNotFound("Opportunity assessment not found")
    return assessment


@router.post("/companies/{company_id}/opportunity-assessment/recalculate", response_model=AssessmentResponse)
def recalculate_opportunity(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.recalculate_opportunity(db, company_id, organization_id)


@router.get("/companies/{company_id}/next-best-action", response_model=ActionResponse)
def next_action(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_access(db, user, organization_id)
    action = service.get_next_action(db, company_id, organization_id)
    if action is None:
        raise CompanyIntelligenceNotFound("Next best action not found")
    return action


@router.post("/companies/{company_id}/next-best-action/recalculate", response_model=ActionResponse)
def recalculate_next_action(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = organization_for_company(db, company_id)
    require_organization_write(db, user, organization_id)
    return service.recalculate_next_action(db, company_id, organization_id)