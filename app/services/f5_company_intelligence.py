import re
from datetime import datetime, timedelta

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.company import Company
from app.models.f5_company_intelligence import F5Assessment, F5CompanyProfile, F5EvidenceClaim, F5RegionalPresence


def normalize_company_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    # Only normalize common legal suffix spelling; do not infer identity or merge records.
    normalized = re.sub(r"\bprivate limited\b", "pvt ltd", normalized)
    return re.sub(r"\s+", " ", normalized)


def freshness_for_dates(*dates: datetime | None, now: datetime | None = None):
    """Return the documented F5 freshness bucket from the newest available date.

    FRESH is <=90 days old, AGING is 91-365 days old, and STALE is older.
    Missing dates remain UNKNOWN; callers may use the persisted value when a
    source has supplied an explicit review state.
    """
    from app.models.f5_company_intelligence import F5Freshness

    newest = max((date for date in dates if date is not None), default=None)
    if newest is None:
        return F5Freshness.UNKNOWN
    age = (now or datetime.utcnow()) - newest
    if age <= timedelta(days=90):
        return F5Freshness.FRESH
    if age <= timedelta(days=365):
        return F5Freshness.AGING
    return F5Freshness.STALE


class F5CompanyIntelligenceService:
    def _company(self, db: Session, company_id: int, organization_id: int):
        return db.scalar(select(Company).where(Company.id == company_id, Company.organization_id == organization_id))

    def list(self, db: Session, organization_id: int, page: int, page_size: int, search: str | None = None, industry: str | None = None, lifecycle_status=None, suitability=None, geography: str | None = None, confidence: float | None = None, freshness=None, duplicate_status=None):
        profile_join = and_(F5CompanyProfile.company_id == Company.id, F5CompanyProfile.organization_id == organization_id)
        assessment_join = and_(F5Assessment.company_id == Company.id, F5Assessment.organization_id == organization_id)
        query = select(Company, F5CompanyProfile, F5Assessment).where(Company.organization_id == organization_id).outerjoin(F5CompanyProfile, profile_join).outerjoin(F5Assessment, assessment_join)
        if search:
            term = f"%{search.strip()}%"
            query = query.where(or_(Company.company_name.ilike(term), Company.industry.ilike(term), Company.headquarters_city.ilike(term), Company.headquarters_state.ilike(term)))
        if industry:
            query = query.where(Company.industry.ilike(f"%{industry.strip()}%"))
        if geography:
            term = f"%{geography.strip()}%"
            regional_match = exists(
                select(F5RegionalPresence.id)
                .where(
                    F5RegionalPresence.profile_id == F5CompanyProfile.id,
                    F5RegionalPresence.region.ilike(term),
                )
            )
            query = query.where(or_(Company.headquarters_city.ilike(term), Company.headquarters_state.ilike(term), regional_match))
        if lifecycle_status:
            query = query.where(F5CompanyProfile.lifecycle_status == lifecycle_status)
        if suitability:
            query = query.where(F5Assessment.warehouse_suitability == suitability)
        if confidence is not None:
            query = query.where(F5Assessment.confidence >= confidence)
        if freshness:
            query = query.where(F5Assessment.freshness == freshness)
        if duplicate_status:
            query = query.where(F5CompanyProfile.duplicate_status == duplicate_status)
        count_subquery = query.order_by(None).with_only_columns(Company.id).distinct().subquery()
        count_query = select(func.count()).select_from(count_subquery)
        total = db.scalar(count_query) or 0
        rows = db.execute(query.order_by(Company.company_name, Company.id).offset((page - 1) * page_size).limit(page_size)).unique().all()
        return rows, total

    def detail(self, db: Session, company_id: int, organization_id: int):
        company = self._company(db, company_id, organization_id)
        if company is None:
            return None
        profile = db.scalar(select(F5CompanyProfile).where(F5CompanyProfile.company_id == company_id, F5CompanyProfile.organization_id == organization_id).options(selectinload(F5CompanyProfile.presence), selectinload(F5CompanyProfile.claims)))
        assessment = db.scalar(select(F5Assessment).where(F5Assessment.company_id == company_id, F5Assessment.organization_id == organization_id))
        return company, profile, assessment

    def save_profile(self, db, company_id, organization_id, data):
        if self._company(db, company_id, organization_id) is None:
            return None
        row = db.scalar(select(F5CompanyProfile).where(F5CompanyProfile.company_id == company_id, F5CompanyProfile.organization_id == organization_id))
        if row is None:
            row = F5CompanyProfile(company_id=company_id, organization_id=organization_id, **data.model_dump())
            db.add(row)
        else:
            for key, value in data.model_dump().items(): setattr(row, key, value)
        db.commit(); db.refresh(row); return row

    def save_assessment(self, db, company_id, organization_id, data):
        if self._company(db, company_id, organization_id) is None: return None
        row = db.scalar(select(F5Assessment).where(F5Assessment.company_id == company_id, F5Assessment.organization_id == organization_id))
        if row is None: row = F5Assessment(company_id=company_id, organization_id=organization_id, **data.model_dump()); db.add(row)
        else:
            for key, value in data.model_dump().items(): setattr(row, key, value)
        row.evidence_count = db.scalar(select(func.count(F5EvidenceClaim.id)).join(F5CompanyProfile).where(F5CompanyProfile.company_id == company_id, F5CompanyProfile.organization_id == organization_id)) or 0
        db.commit(); db.refresh(row); return row

    def add_presence(self, db, company_id, organization_id, data):
        profile = db.scalar(select(F5CompanyProfile).where(F5CompanyProfile.company_id == company_id, F5CompanyProfile.organization_id == organization_id))
        if profile is None: return None
        row = F5RegionalPresence(profile_id=profile.id, **data.model_dump()); db.add(row); db.commit(); db.refresh(row); return row

    def add_claim(self, db, company_id, organization_id, data):
        profile = db.scalar(select(F5CompanyProfile).where(F5CompanyProfile.company_id == company_id, F5CompanyProfile.organization_id == organization_id))
        if profile is None: return None
        row = F5EvidenceClaim(profile_id=profile.id, **data.model_dump()); db.add(row); db.commit(); db.refresh(row); return row