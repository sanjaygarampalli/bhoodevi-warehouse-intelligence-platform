from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_intelligence import CompanyContact, CompanyContactMethod, ContactMethodType, VerificationStatus
from app.models.contact_workflow import ContactOutreachActivity
from app.models.deal import Deal
from app.models.lead import Lead
from app.models.requirement import Requirement
from app.models.response_qualification import ResponseQualificationAssessment
from app.schemas.company import CompanyCreate
from app.schemas.response_qualification import ContactResolutionRequest, QualificationWrite


class ResponseQualificationService:
    @staticmethod
    def normalize_name(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def normalize_domain(value: str | None) -> str | None:
        if not value:
            return None
        parsed = urlparse(value if "://" in value else f"https://{value}")
        return (parsed.hostname or "").casefold().removeprefix("www.") or None

    def resolve_company(self, db: Session, organization_id: int, company_name: str, website: str | None):
        companies = list(db.scalars(select(Company).where(Company.organization_id == organization_id)).all())
        name = self.normalize_name(company_name)
        domain = self.normalize_domain(website)
        exact = [c for c in companies if self.normalize_name(c.company_name) == name or (domain and self.normalize_domain(c.website) == domain)]
        if len(exact) == 1:
            return {"result": "EXACT_MATCH", "human_review_required": False, "recommended_action": "ENRICH_EXISTING_COMPANY", "company_id": exact[0].id}
        possible = [c.id for c in companies if name in self.normalize_name(c.company_name) or self.normalize_name(c.company_name) in name]
        return {"result": "POSSIBLE_MATCH" if possible else "NO_MATCH", "human_review_required": bool(possible), "recommended_action": "HUMAN_REVIEW" if possible else "CREATE_COMPANY", "possible_company_ids": possible}

    def consolidate_company(self, db: Session, payload: CompanyCreate):
        resolution = self.resolve_company(db, payload.organization_id, payload.company_name, payload.website)
        if resolution["result"] == "EXACT_MATCH":
            company = db.get(Company, resolution["company_id"])
            for key, value in payload.model_dump(exclude={"organization_id"}, exclude_unset=True).items():
                if value is not None and not getattr(company, key):
                    setattr(company, key, value)
            db.commit()
            db.refresh(company)
            return resolution | {"company": company}
        if resolution["result"] == "POSSIBLE_MATCH":
            return resolution
        company = Company(**payload.model_dump())
        db.add(company)
        db.commit()
        db.refresh(company)
        return {"result": "CREATED", "human_review_required": False, "recommended_action": "STORE_INTELLIGENCE", "company_id": company.id, "company": company}

    def resolve_contact(self, db: Session, company_id: int, payload: ContactResolutionRequest):
        contacts = list(db.scalars(select(CompanyContact).where(CompanyContact.company_id == company_id)).all())
        emails = {payload.email.strip().casefold()} if payload.email else set()
        linkedin = payload.linkedin.strip().casefold() if payload.linkedin else None
        matches = []
        for contact in contacts:
            methods = list(db.scalars(select(CompanyContactMethod).where(CompanyContactMethod.contact_id == contact.id)).all())
            if any(m.normalized_value in emails or (linkedin and m.normalized_value == linkedin) for m in methods):
                matches.append(contact)
        if len(matches) == 1:
            return {"result": "EXACT_MATCH", "human_review_required": False, "recommended_action": "ENRICH_EXISTING_CONTACT", "contact_id": matches[0].id}
        return {"result": "POSSIBLE_MATCH" if matches else "NO_MATCH", "human_review_required": bool(matches), "recommended_action": "HUMAN_REVIEW" if matches else "CREATE_CONTACT", "possible_contact_ids": [c.id for c in matches]}

    def consolidate_contact(self, db: Session, company_id: int, payload: ContactResolutionRequest):
        company = db.get(Company, company_id)
        if company is None:
            raise LookupError("Company not found")
        resolution = self.resolve_contact(db, company_id, payload)
        if resolution["result"] == "POSSIBLE_MATCH":
            return resolution
        if resolution["result"] == "EXACT_MATCH":
            contact = db.get(CompanyContact, resolution["contact_id"])
            if payload.full_name and not contact.full_name:
                contact.full_name = payload.full_name
            if payload.job_title and not contact.job_title:
                contact.job_title = payload.job_title
            db.commit()
            return resolution | {"contact": contact}
        contact = CompanyContact(
            organization_id=company.organization_id,
            company_id=company_id,
            full_name=payload.full_name,
            job_title=payload.job_title,
            department=payload.department,
            seniority=payload.seniority,
        )
        db.add(contact)
        db.flush()
        for method_type, value in ((ContactMethodType.EMAIL, payload.email), (ContactMethodType.LINKEDIN, payload.linkedin)):
            if value:
                normalized = value.strip().casefold()
                db.add(CompanyContactMethod(contact_id=contact.id, method_type=method_type, value=value, normalized_value=normalized, verification_status=payload.method_verification, is_verified=payload.method_verification == VerificationStatus.VERIFIED))
        db.commit()
        db.refresh(contact)
        return {"result": "CREATED", "human_review_required": False, "recommended_action": "STORE_INTELLIGENCE", "contact_id": contact.id, "contact": contact}

    def commercial_context(self, db: Session, company_id: int):
        lead_ids = [x for x in db.scalars(select(Lead.id).where(Lead.company_id == company_id, Lead.status.not_in(("WON", "LOST", "DISQUALIFIED"))))]
        requirement_ids = [x for x in db.scalars(select(Requirement.id).where(Requirement.lead_id.in_(lead_ids), Requirement.status.in_(("DRAFT", "ACTIVE", "ON_HOLD"))))] if lead_ids else []
        deal_ids = [x for x in db.scalars(select(Deal.id).where(Deal.lead_id.in_(lead_ids), Deal.deal_status == "OPEN"))] if lead_ids else []
        qualification_ids = [x for x in db.scalars(select(ResponseQualificationAssessment.id).where(ResponseQualificationAssessment.company_id == company_id))]
        context = "ACTIVE_DEAL" if deal_ids else "ACTIVE_REQUIREMENT" if requirement_ids else "ACTIVE_LEAD" if lead_ids else "QUALIFICATION_IN_PROGRESS" if qualification_ids else "MARKET_INTELLIGENCE_ONLY"
        return {"company_id": company_id, "active_lead_ids": lead_ids, "active_requirement_ids": requirement_ids, "active_deal_ids": deal_ids, "qualification_ids": qualification_ids, "context": context, "recommended_next_action": "Review existing commercial records before progression." if lead_ids or requirement_ids or deal_ids else "Continue human research and qualification.", "human_review_required": True}

    def qualification(self, db: Session, company_id: int, contact_id: int, outreach_id: int, user_id: int, payload: QualificationWrite, assessment_id: int | None = None):
        company = db.get(Company, company_id)
        outreach = db.scalar(select(ContactOutreachActivity).where(ContactOutreachActivity.id == outreach_id, ContactOutreachActivity.company_id == company_id, ContactOutreachActivity.contact_id == contact_id))
        contact = db.scalar(select(CompanyContact).where(CompanyContact.id == contact_id, CompanyContact.company_id == company_id))
        if not company or not contact or not outreach or outreach.organization_id != company.organization_id or contact.organization_id != company.organization_id:
            raise LookupError("Qualification ownership chain is invalid")
        record = db.get(ResponseQualificationAssessment, assessment_id) if assessment_id else ResponseQualificationAssessment()
        if assessment_id and (record is None or record.company_id != company_id or record.outreach_activity_id != outreach_id):
            raise LookupError("Qualification not found")
        for key, value in payload.model_dump().items():
            setattr(record, key, value.value if hasattr(value, "value") else value)
        record.organization_id, record.company_id, record.contact_id, record.outreach_activity_id = company.organization_id, company_id, contact_id, outreach_id
        record.reviewer_user_id = user_id
        record.human_review_required = True
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def get_qualification(self, db: Session, company_id: int, assessment_id: int):
        record = db.scalar(select(ResponseQualificationAssessment).where(ResponseQualificationAssessment.id == assessment_id, ResponseQualificationAssessment.company_id == company_id))
        if record is None:
            raise LookupError("Qualification not found")
        return record

    def qualification_history(self, db: Session, company_id: int, contact_id: int):
        return list(db.scalars(select(ResponseQualificationAssessment).where(ResponseQualificationAssessment.company_id == company_id, ResponseQualificationAssessment.contact_id == contact_id).order_by(ResponseQualificationAssessment.updated_at.desc(), ResponseQualificationAssessment.id.desc())))