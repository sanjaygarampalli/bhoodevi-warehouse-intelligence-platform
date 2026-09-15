from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.contact_workflow import InvestigationResponse, InvestigationWrite, OutreachResponse, OutreachUpdate, OutreachWrite, PipelineContext
from app.services.contact_workflow import ContactWorkflowService
from app.services.organization_access import require_organization_access, require_organization_write

router = APIRouter(prefix="/companies/{company_id}/contacts/{contact_id}", tags=["Contact Workflow"])
service = ContactWorkflowService()


def authorize(db, user, company_id, write=False):
    from app.models.company import Company
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    (require_organization_write if write else require_organization_access)(db, user, company.organization_id)
    return company


@router.post("/investigation", response_model=InvestigationResponse)
def create_investigation(company_id: int, contact_id: int, payload: InvestigationWrite, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id, True)
    try:
        return service.save_investigation(db, company_id, contact_id, current_user.id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/investigation", response_model=InvestigationResponse | None)
def read_investigation(company_id: int, contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id)
    try:
        return service.get_investigation(db, company_id, contact_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/investigation", response_model=InvestigationResponse)
def update_investigation(company_id: int, contact_id: int, payload: InvestigationWrite, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_investigation(company_id, contact_id, payload, db, current_user)


@router.post("/select-for-outreach", response_model=InvestigationResponse)
def select_contact(company_id: int, contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id, True)
    try:
        return service.select_for_outreach(db, company_id, contact_id, current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/outreach", response_model=OutreachResponse)
def record_outreach(company_id: int, contact_id: int, payload: OutreachWrite, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id, True)
    try:
        return service.create_outreach(db, company_id, contact_id, current_user.id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/outreach-history", response_model=list[OutreachResponse])
def outreach_history(company_id: int, contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id)
    try:
        return service.history(db, company_id, contact_id)[1]
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/outreach/{activity_id}", response_model=OutreachResponse)
def update_outreach(company_id: int, contact_id: int, activity_id: int, payload: OutreachUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id, True)
    try:
        return service.update_outreach(db, company_id, contact_id, activity_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/pipeline-context", response_model=PipelineContext)
def pipeline_context(company_id: int, contact_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id)
    try:
        service.contact(db, company_id, contact_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.pipeline_context(db, company_id)


company_history_router = APIRouter(prefix="/companies/{company_id}", tags=["Contact Workflow"])


@company_history_router.get("/contact-activity-history", response_model=list[OutreachResponse])
def company_contact_history(company_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    authorize(db, current_user, company_id)
    return service.company_history(db, company_id)