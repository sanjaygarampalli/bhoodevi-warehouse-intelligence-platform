from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate
from app.schemas.response_qualification import (
    CommercialContextResponse,
    CompanyResolutionRequest,
    ContactResolutionRequest,
    QualificationResponse,
    QualificationWrite,
    ResolutionResponse,
    ExplicitLeadProgression,
)
from app.schemas.lead import LeadCreate
from app.services.lead import LeadService
from app.services.organization_access import require_organization_access, require_organization_write
from app.services.response_qualification import ResponseQualificationService

router = APIRouter(tags=["Response Qualification"])
service = ResponseQualificationService()
lead_service = LeadService()


@router.post("/companies/intelligence-resolution", response_model=ResolutionResponse)
def resolve_company(payload: CompanyResolutionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_organization_access(db, user, payload.organization_id)
    return service.resolve_company(db, payload.organization_id, payload.company_name, payload.website)


@router.post("/companies/intelligence-consolidation")
def consolidate_company(payload: CompanyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_organization_write(db, user, payload.organization_id)
    result = service.consolidate_company(db, payload)
    return {key: value for key, value in result.items() if key != "company"} | ({"company": result["company"]} if "company" in result else {})


@router.post("/companies/{company_id}/contacts/intelligence-resolution", response_model=ResolutionResponse)
def resolve_contact(company_id: int, payload: ContactResolutionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_access(db, user, company.organization_id)
    return service.resolve_contact(db, company_id, payload)


@router.post("/companies/{company_id}/contacts/intelligence-consolidation")
def consolidate_contact(company_id: int, payload: ContactResolutionRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_write(db, user, company.organization_id)
    result = service.consolidate_contact(db, company_id, payload)
    return {key: value for key, value in result.items() if key != "contact"} | ({"contact": result["contact"]} if "contact" in result else {})


@router.get("/companies/{company_id}/commercial-context", response_model=CommercialContextResponse)
def commercial_context(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_access(db, user, company.organization_id)
    return service.commercial_context(db, company_id)


@router.get("/companies/{company_id}/contacts/{contact_id}/qualifications", response_model=list[QualificationResponse])
def qualification_history(company_id: int, contact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_access(db, user, company.organization_id)
    return service.qualification_history(db, company_id, contact_id)


@router.get("/companies/{company_id}/qualifications/{assessment_id}", response_model=QualificationResponse)
def read_qualification(company_id: int, assessment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_access(db, user, company.organization_id)
    try:
        return service.get_qualification(db, company_id, assessment_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/companies/{company_id}/contacts/{contact_id}/outreach/{outreach_id}/qualification", response_model=QualificationResponse, status_code=status.HTTP_201_CREATED)
def create_qualification(company_id: int, contact_id: int, outreach_id: int, payload: QualificationWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_write(db, user, company.organization_id)
    try:
        return service.qualification(db, company_id, contact_id, outreach_id, user.id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/companies/{company_id}/contacts/{contact_id}/outreach/{outreach_id}/qualification/{assessment_id}", response_model=QualificationResponse)
def update_qualification(company_id: int, contact_id: int, outreach_id: int, assessment_id: int, payload: QualificationWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_write(db, user, company.organization_id)
    try:
        return service.qualification(db, company_id, contact_id, outreach_id, user.id, payload, assessment_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/companies/{company_id}/explicit-lead-progression", response_model=dict, status_code=status.HTTP_201_CREATED)
def explicit_lead_progression(company_id: int, payload: ExplicitLeadProgression, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    require_organization_write(db, user, company.organization_id)
    context = service.commercial_context(db, company_id)
    if context["active_lead_ids"]:
        raise HTTPException(status_code=409, detail="An active lead already exists for this company")
    created = lead_service.create_lead(db, LeadCreate(lead_number=payload.lead_number, company_id=company_id))
    if created is None:
        raise HTTPException(status_code=409, detail="Lead could not be created")
    return {"lead": created, "human_decision_required": True}