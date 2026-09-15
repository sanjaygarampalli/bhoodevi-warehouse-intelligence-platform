from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_intelligence import CompanyContact
from app.models.contact_workflow import ContactInvestigation, ContactOutreachActivity
from app.models.deal import Deal
from app.models.lead import Lead
from app.models.requirement import Requirement
from app.schemas.contact_workflow import InvestigationWrite, OutreachUpdate, OutreachWrite


class ContactWorkflowConflict(ValueError):
    pass


class ContactWorkflowService:
    def contact(self, db: Session, company_id: int, contact_id: int):
        contact = db.scalar(select(CompanyContact).where(CompanyContact.id == contact_id, CompanyContact.company_id == company_id))
        if contact is None:
            raise LookupError("Contact not found for company")
        company = db.get(Company, company_id)
        if company is None or contact.organization_id != company.organization_id:
            raise ContactWorkflowConflict("Contact ownership does not match company")
        return contact, company

    def pipeline_context(self, db: Session, company_id: int) -> dict:
        leads = list(db.scalars(select(Lead).where(Lead.company_id == company_id, Lead.status.not_in(("WON", "LOST", "DISQUALIFIED")))))
        lead_ids = [lead.id for lead in leads]
        requirements = list(db.scalars(select(Requirement).where(Requirement.lead_id.in_(lead_ids), Requirement.status.in_(("DRAFT", "ACTIVE", "ON_HOLD"))))) if lead_ids else []
        deals = list(db.scalars(select(Deal).where(Deal.lead_id.in_(lead_ids), Deal.deal_status == "OPEN"))) if lead_ids else []
        active = bool(leads or requirements or deals)
        return {"active_pipeline_exists": active, "active_lead_ids": lead_ids, "active_requirement_ids": [r.id for r in requirements], "active_deal_ids": [d.id for d in deals], "recommendation": "Review the existing commercial workflow before creating duplicate outreach." if active else "No active commercial pipeline found."}

    def get_investigation(self, db, company_id, contact_id):
        self.contact(db, company_id, contact_id)
        return db.scalar(select(ContactInvestigation).where(ContactInvestigation.contact_id == contact_id))

    def save_investigation(self, db: Session, company_id: int, contact_id: int, user_id: int, payload: InvestigationWrite):
        contact, company = self.contact(db, company_id, contact_id)
        record = db.scalar(select(ContactInvestigation).where(ContactInvestigation.contact_id == contact_id))
        if record is None:
            record = ContactInvestigation(organization_id=company.organization_id, company_id=company.id, contact_id=contact.id)
            db.add(record)
        for key, value in payload.model_dump().items():
            setattr(record, key, value.value if hasattr(value, "value") else value)
        record.investigated_by_user_id = user_id
        db.commit()
        db.refresh(record)
        return record

    def select_for_outreach(self, db, company_id, contact_id, user_id):
        record = self.get_investigation(db, company_id, contact_id)
        if record is None:
            record = self.save_investigation(db, company_id, contact_id, user_id, InvestigationWrite(investigation_status="VERIFIED"))
        record.selected_for_outreach = True
        record.investigated_by_user_id = user_id
        db.commit()
        db.refresh(record)
        return record

    def create_outreach(self, db, company_id, contact_id, user_id, payload: OutreachWrite):
        contact, company = self.contact(db, company_id, contact_id)
        record = ContactOutreachActivity(organization_id=company.organization_id, company_id=company.id, contact_id=contact.id, performed_by_user_id=user_id, **payload.model_dump())
        for field in ("method", "outcome"):
            value = getattr(record, field)
            if hasattr(value, "value"):
                setattr(record, field, value.value)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def history(self, db, company_id, contact_id):
        self.contact(db, company_id, contact_id)
        investigation = self.get_investigation(db, company_id, contact_id)
        outreach = list(db.scalars(select(ContactOutreachActivity).where(ContactOutreachActivity.company_id == company_id, ContactOutreachActivity.contact_id == contact_id).order_by(ContactOutreachActivity.performed_at.desc(), ContactOutreachActivity.created_at.desc(), ContactOutreachActivity.id.desc())))
        return investigation, outreach

    def update_outreach(self, db, company_id, contact_id, activity_id, payload: OutreachUpdate):
        self.contact(db, company_id, contact_id)
        record = db.scalar(select(ContactOutreachActivity).where(ContactOutreachActivity.id == activity_id, ContactOutreachActivity.company_id == company_id, ContactOutreachActivity.contact_id == contact_id))
        if record is None:
            raise LookupError("Outreach activity not found")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, key, value.value if hasattr(value, "value") else value)
        db.commit()
        db.refresh(record)
        return record

    def company_history(self, db, company_id):
        return list(db.scalars(select(ContactOutreachActivity).where(ContactOutreachActivity.company_id == company_id).order_by(ContactOutreachActivity.performed_at.desc(), ContactOutreachActivity.created_at.desc(), ContactOutreachActivity.id.desc())))