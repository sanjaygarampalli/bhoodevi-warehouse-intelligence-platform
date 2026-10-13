from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.requirement import RequirementStatus
from app.models.requirement_intelligence import RequirementIntelligenceEvidence
from app.models.user import User
from app.schemas.requirement_intelligence import (
    RequirementAssessmentResponse,
    RequirementEvidenceCreate,
    RequirementEvidenceResponse,
    RequirementEvidenceUpdate,
    RequirementIntelligenceResponse,
)
from app.services.organization_access import require_organization_access, require_organization_write
from app.services.requirement_intelligence import RequirementEvidenceConflict, RequirementIntelligenceService

router = APIRouter(prefix="/requirement-intelligence", tags=["Requirement Intelligence"])
service = RequirementIntelligenceService()


def requirement_or_404(db: Session, requirement_id: int):
    requirement = service.get_requirement(db, requirement_id)
    if requirement is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return requirement


def scoped_requirement(db: Session, user: User, requirement_id: int):
    requirement = requirement_or_404(db, requirement_id)
    organization_id = service.organization_id(db, requirement_id)
    if organization_id is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    require_organization_access(db, user, organization_id)
    return requirement, organization_id


@router.get("", response_model=list[RequirementIntelligenceResponse])
def list_requirement_intelligence(
    organization_id: int = Query(..., gt=0),
    requirement_status: RequirementStatus | None = Query(default=None, alias="status"),
    query: str | None = Query(default=None, max_length=100),
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_organization_access(db, current_user, organization_id)
    response = []
    for requirement in service.list_requirements(db, organization_id, status=requirement_status, query=query, limit=limit, offset=offset):
        company = service.company_for(db, requirement)
        response.append(RequirementIntelligenceResponse(
            organization_id=company.organization_id,
            requirement=requirement, company_name=company.company_name,
            evidence=service.evidence(db, requirement.id),
            assessment=service.assessment(db, requirement),
            market_signal_ids=service.market_signal_ids(db, requirement.id),
        ))
    return response


@router.get("/{requirement_id}", response_model=RequirementIntelligenceResponse)
def get_requirement_intelligence(requirement_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    requirement, organization_id = scoped_requirement(db, current_user, requirement_id)
    return RequirementIntelligenceResponse(
        organization_id=organization_id,
        requirement=requirement, company_name=service.company_for(db, requirement).company_name,
        evidence=service.evidence(db, requirement.id), assessment=service.assessment(db, requirement),
        market_signal_ids=service.market_signal_ids(db, requirement.id),
    )


@router.get("/{requirement_id}/assessment", response_model=RequirementAssessmentResponse)
def get_requirement_assessment(requirement_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    requirement, _ = scoped_requirement(db, current_user, requirement_id)
    return service.assessment(db, requirement)


@router.get("/{requirement_id}/evidence", response_model=list[RequirementEvidenceResponse])
def list_requirement_evidence(requirement_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    requirement, _ = scoped_requirement(db, current_user, requirement_id)
    return service.evidence(db, requirement.id)


@router.post("/{requirement_id}/evidence", response_model=RequirementEvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_requirement_evidence(requirement_id: int, data: RequirementEvidenceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    requirement, _ = scoped_requirement(db, current_user, requirement_id)
    require_organization_write(db, current_user, service.organization_id(db, requirement.id))
    try:
        return service.create_evidence(db, requirement, data)
    except RequirementEvidenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/{requirement_id}/evidence/{evidence_id}", response_model=RequirementEvidenceResponse)
def update_requirement_evidence(requirement_id: int, evidence_id: int, data: RequirementEvidenceUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    requirement, _ = scoped_requirement(db, current_user, requirement_id)
    require_organization_write(db, current_user, service.organization_id(db, requirement.id))
    evidence = db.get(RequirementIntelligenceEvidence, evidence_id)
    if evidence is None or evidence.requirement_id != requirement.id:
        raise HTTPException(status_code=404, detail="Requirement evidence not found")
    try:
        return service.update_evidence(db, evidence, data, current_user)
    except RequirementEvidenceConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
