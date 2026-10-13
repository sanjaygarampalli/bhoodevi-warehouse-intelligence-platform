from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.f5_company_intelligence import F5Assessment, F5CompanyProfile, F5DuplicateStatus, F5Freshness, F5LifecycleStatus, F5WarehouseSuitability
from app.models.organization_membership import MembershipStatus, OrganizationMembership
from app.models.user import User
from app.schemas.f5_company_intelligence import F5AssessmentResponse, F5AssessmentWrite, F5ClaimResponse, F5ClaimWrite, F5CompanyDetail, F5CompanyPage, F5CompanySummary, F5PresenceResponse, F5PresenceWrite, F5ProfileResponse, F5ProfileWrite
from app.services.f5_company_intelligence import F5CompanyIntelligenceService
from app.services.organization_access import organization_for_company, require_organization_access, require_organization_write

router = APIRouter(prefix="/f5", tags=["F5 Company Intelligence"])
service = F5CompanyIntelligenceService()


def _summary(company, profile, assessment):
    return F5CompanySummary(id=company.id, organization_id=company.organization_id, company_name=company.company_name, legal_name=company.legal_name, industry=company.industry, company_type=company.company_type, website=company.website, headquarters_city=company.headquarters_city, headquarters_state=company.headquarters_state, profile=profile, assessment=assessment)


@router.get("/companies", response_model=F5CompanyPage)
def list_f5_companies(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), organization_id: int | None = Query(None, gt=0), search: str | None = None, industry: str | None = None, geography: str | None = None, lifecycle_status: F5LifecycleStatus | None = None, warehouse_suitability: F5WarehouseSuitability | None = None, confidence: float | None = Query(None, ge=0, le=1), freshness: F5Freshness | None = None, duplicate_status: F5DuplicateStatus | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "admin" and organization_id is None:
        raise HTTPException(status_code=400, detail="organization_id is required for global administrators")
    if user.role != "admin":
        memberships = db.scalars(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.status == MembershipStatus.ACTIVE,
                *([OrganizationMembership.organization_id == organization_id] if organization_id else []),
            )
            .order_by(OrganizationMembership.organization_id)
        ).all()
        if organization_id is None and len(memberships) > 1:
            raise HTTPException(status_code=400, detail="organization_id is required when multiple organizations are active")
        organization_id = memberships[0].organization_id if memberships else None
    if organization_id is None: raise HTTPException(status_code=403, detail="Active organization membership required")
    require_organization_access(db, user, organization_id)
    rows, total = service.list(db, organization_id, page, page_size, search, industry, lifecycle_status, warehouse_suitability, geography, confidence, freshness, duplicate_status)
    result = [_summary(company, profile, assessment) for company, profile, assessment in rows]
    return {"items": result, "page": page, "page_size": page_size, "total": total}


def _org(db, user, company_id):
    organization_id = organization_for_company(db, company_id)
    if organization_id is None: raise HTTPException(status_code=404, detail="Company not found")
    require_organization_access(db, user, organization_id)
    return organization_id


@router.get("/companies/{company_id}", response_model=F5CompanyDetail)
def get_f5_company(company_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = _org(db, user, company_id)
    result = service.detail(db, company_id, organization_id)
    if result is None: raise HTTPException(status_code=404, detail="Company not found")
    company, profile, assessment = result
    return {"id": company.id, "organization_id": company.organization_id, "company_name": company.company_name, "legal_name": company.legal_name, "industry": company.industry, "company_type": company.company_type, "website": company.website, "headquarters_city": company.headquarters_city, "headquarters_state": company.headquarters_state, "profile": profile, "assessment": assessment, "presence": profile.presence if profile else [], "evidence": profile.claims if profile else [], "current_warehouse_requirement": {"value": None, "classification": "UNKNOWN"}}


@router.put("/companies/{company_id}/profile", response_model=F5ProfileResponse)
def put_f5_profile(company_id: int, data: F5ProfileWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = _org(db, user, company_id); require_organization_write(db, user, organization_id)
    row = service.save_profile(db, company_id, organization_id, data)
    if row is None: raise HTTPException(status_code=404, detail="Company not found")
    return row


@router.post("/companies/{company_id}/regional-presence", response_model=F5PresenceResponse, status_code=status.HTTP_201_CREATED)
def add_f5_presence(company_id: int, data: F5PresenceWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = _org(db, user, company_id); require_organization_write(db, user, organization_id)
    row = service.add_presence(db, company_id, organization_id, data)
    if row is None: raise HTTPException(status_code=404, detail="F5 profile not found")
    return row


@router.post("/companies/{company_id}/evidence", response_model=F5ClaimResponse, status_code=status.HTTP_201_CREATED)
def add_f5_claim(company_id: int, data: F5ClaimWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = _org(db, user, company_id); require_organization_write(db, user, organization_id)
    row = service.add_claim(db, company_id, organization_id, data)
    if row is None: raise HTTPException(status_code=404, detail="F5 profile not found")
    return row


@router.put("/companies/{company_id}/icp", response_model=F5AssessmentResponse)
def put_f5_assessment(company_id: int, data: F5AssessmentWrite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    organization_id = _org(db, user, company_id); require_organization_write(db, user, organization_id)
    row = service.save_assessment(db, company_id, organization_id, data)
    if row is None: raise HTTPException(status_code=404, detail="Company not found")
    return row