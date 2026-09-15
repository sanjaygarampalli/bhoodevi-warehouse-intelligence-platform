"""Read-only, explainable relevance assessments for stored company contacts."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.company import Company
from app.models.company_intelligence import (
    CompanyContact,
    CompanyContactMethod,
    ContactDepartment,
    ContactMethodType,
    ContactSeniority,
)
from app.models.deal import Deal
from app.models.lead import Lead, LeadStatus
from app.models.market_signal import MarketSignal, MarketSignalStatus, MarketSignalType
from app.models.requirement import Requirement, RequirementStatus
from app.schemas.company_prospect_priority import CompanyProspectPriority
from app.schemas.company_intelligence import (
    DecisionMakerAssessmentResponse,
    DecisionMakerQueueItemResponse,
    DecisionMakerQueueResponse,
    DecisionMakerRelevance,
    DecisionMakerCompanyResponse,
)
from app.services.company_intelligence import CompanyIntelligenceOrganizationError
from app.services.company_prospect_priority import CompanyProspectPriorityService


class DecisionMakerRelevanceService:
    """Compute contact relevance without changing contacts or commercial records."""

    functional_departments = {
        ContactDepartment.LOGISTICS,
        ContactDepartment.SUPPLY_CHAIN,
        ContactDepartment.WAREHOUSE,
        ContactDepartment.OPERATIONS,
    }
    adjacent_departments = {
        ContactDepartment.PROCUREMENT,
        ContactDepartment.FACILITY,
        ContactDepartment.REAL_ESTATE,
        ContactDepartment.EXPANSION,
        ContactDepartment.BUSINESS_DEVELOPMENT,
    }
    strategic_seniority = {
        ContactSeniority.OWNER,
        ContactSeniority.FOUNDER,
        ContactSeniority.C_LEVEL,
        ContactSeniority.VP,
        ContactSeniority.DIRECTOR,
    }
    verified_demand_types = {
        MarketSignalType.NEW_WAREHOUSE,
        MarketSignalType.NEW_DISTRIBUTION_CENTER,
        MarketSignalType.LOGISTICS_EXPANSION,
        MarketSignalType.DISTRIBUTION_EXPANSION,
    }

    def _company(self, db: Session, company_id: int, organization_id: int) -> Company:
        company = db.scalar(select(Company).where(
            Company.id == company_id,
            Company.organization_id == organization_id,
        ))
        if company is None:
            raise CompanyIntelligenceOrganizationError("Company is not accessible in this organization")
        return company

    @staticmethod
    def _pipeline_context(db: Session, company: Company) -> dict[str, bool | str]:
        leads = list(db.scalars(select(Lead).where(Lead.company_id == company.id)).all())
        active_leads = [lead for lead in leads if lead.status not in {
            LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED,
        }]
        requirements = list(db.scalars(
            select(Requirement).join(Lead, Requirement.lead_id == Lead.id).where(
                Lead.company_id == company.id,
                Requirement.requirement_status.in_([
                    RequirementStatus.DRAFT,
                    RequirementStatus.ACTIVE,
                    RequirementStatus.ON_HOLD,
                ]),
            )
        ).all())
        deals = list(db.scalars(
            select(Deal).join(Lead, Deal.lead_id == Lead.id).where(
                Deal.organization_id == company.organization_id,
                Lead.company_id == company.id,
                Deal.deal_status == "OPEN",
            )
        ).all())
        return {
            "existing_lead": bool(active_leads),
            "existing_requirement": bool(requirements),
            "active_deal": bool(deals),
            "pipeline_status": "ACTIVE OPPORTUNITY" if deals else "QUALIFICATION IN PROGRESS" if requirements or active_leads else "NEW PROSPECT",
        }

    @staticmethod
    def _method_flags(contact: CompanyContact) -> dict[str, bool]:
        types = {method.method_type for method in contact.methods}
        return {
            "has_email": ContactMethodType.EMAIL in types,
            "has_phone": ContactMethodType.PHONE in types,
            "has_linkedin": ContactMethodType.LINKEDIN in types,
        }

    def _verified_demand(self, db: Session, company: Company) -> bool:
        return db.scalar(select(MarketSignal.id).where(
            MarketSignal.organization_id == company.organization_id,
            MarketSignal.company_id == company.id,
            MarketSignal.status == MarketSignalStatus.VERIFIED,
            MarketSignal.signal_type.in_(self.verified_demand_types),
        ).limit(1)) is not None

    def _assess_contact(
        self,
        contact: CompanyContact,
        prospect: CompanyProspectPriority,
        pipeline: dict[str, bool | str],
        verified_demand: bool,
        company_name: str,
    ) -> DecisionMakerAssessmentResponse:
        title = (contact.job_title or "").lower()
        score = 0
        reasons: list[str] = []
        observed: list[str] = [
            f"Stored designation: {contact.job_title or 'Not recorded'}.",
            f"Stored department: {contact.department.value}.",
            f"Stored seniority: {contact.seniority.value}.",
        ]
        if contact.department in self.functional_departments:
            score += 55
            reasons.append("Stored department indicates warehouse, logistics, supply-chain, or operations responsibility.")
        elif contact.department in self.adjacent_departments:
            score += 35
            reasons.append("Stored department may participate in facilities, procurement, expansion, or commercial decisions.")
        elif contact.department in {ContactDepartment.FINANCE, ContactDepartment.MANAGEMENT}:
            score += 15
            reasons.append("Stored department may contribute to infrastructure or investment decisions.")

        title_terms = ("warehouse", "logistics", "supply chain", "operations", "distribution", "fulfillment", "procurement", "facilities", "real estate", "expansion")
        if any(term in title for term in title_terms):
            score += 20
            reasons.append("Job title contains a warehouse-relevant functional term.")
        if contact.seniority in self.strategic_seniority:
            score += 15
            reasons.append("Senior leadership may have strategic relevance, but seniority alone does not confirm authority.")
        elif contact.seniority in {ContactSeniority.HEAD, ContactSeniority.SENIOR_MANAGER, ContactSeniority.MANAGER}:
            score += 10
            reasons.append("Stored seniority suggests possible functional or operational ownership.")
        if verified_demand and contact.department in (self.functional_departments | self.adjacent_departments):
            score += 10
            reasons.append("Company has a verified warehouse-related market signal relevant to this function.")
            observed.append("A verified warehouse-related market signal is recorded for this company.")

        score = min(score, 100)
        relevance = DecisionMakerRelevance.HIGH if score >= 70 else DecisionMakerRelevance.MEDIUM if score >= 35 else DecisionMakerRelevance.LOW
        methods = self._method_flags(contact)
        available = sum(methods.values())
        contactability = "FULL CONTACT INFORMATION" if available == 3 else "PARTIAL CONTACT INFORMATION" if available else "LIMITED CONTACT INFORMATION"
        observed.append(f"Available contact methods: {contactability.lower()}.")
        uncertainty = ["Decision-making authority is not confirmed from stored contact data."]
        if not all(methods.values()):
            uncertainty.append("Contact method information is incomplete; reachability is not established.")
        if pipeline["active_deal"]:
            recommendation = "Review the existing commercial pipeline before creating additional outreach activity."
            reasons.append("The company currently has an active deal.")
        elif relevance == DecisionMakerRelevance.HIGH and available == 3:
            recommendation = "Review company context and consider human investigation or outreach."
        elif relevance == DecisionMakerRelevance.HIGH:
            recommendation = "Investigate professional contact details before human outreach."
        elif relevance == DecisionMakerRelevance.MEDIUM:
            recommendation = "Keep as a secondary contact for human qualification."
        else:
            recommendation = "Retain for organizational reference; no priority outreach recommendation."
        return DecisionMakerAssessmentResponse(
            contact=contact,
            company=DecisionMakerCompanyResponse(company_id=contact.company_id, company_name=company_name),
            relevance=relevance,
            relevance_score=score,
            reasons=reasons,
            observed_facts=observed,
            inference="The stored role appears relevant to warehouse opportunity investigation; this is an inference, not a confirmed decision-maker fact.",
            recommendation=recommendation,
            uncertainty=uncertainty,
            contact_methods=methods,
            contactability_status=contactability,
            commercial_context=pipeline,
            company_prospect_priority=prospect.priority.value,
            company_prospect_score=prospect.priority_score,
            human_review_required=True,
        )

    def assess_company(self, db: Session, company_id: int, organization_id: int):
        company = self._company(db, company_id, organization_id)
        contacts = list(db.scalars(select(CompanyContact).where(
            CompanyContact.organization_id == organization_id,
            CompanyContact.company_id == company_id,
        ).options(selectinload(CompanyContact.methods)).order_by(CompanyContact.id)).all())
        prospect = CompanyProspectPriorityService()._assess(db, company)
        pipeline = self._pipeline_context(db, company)
        verified_demand = self._verified_demand(db, company)
        assessments = [self._assess_contact(contact, prospect, pipeline, verified_demand, company.company_name) for contact in contacts]
        assessments.sort(key=lambda item: (-item.relevance_score, -sum(item.contact_methods.values()), (item.contact.full_name or "").lower(), item.contact.id))
        return {
            "company_id": company.id,
            "organization_id": organization_id,
            "company_name": company.company_name,
            "prospect_priority": prospect,
            "commercial_context": pipeline,
            "contacts": [item.model_copy(update={"rank": index}) for index, item in enumerate(assessments, 1)],
            "total": len(assessments),
            "human_review_required": True,
        }

    def queue(self, db: Session, organization_id: int, company_id: int | None = None, minimum_relevance: DecisionMakerRelevance | None = None, has_email: bool | None = None, has_phone: bool | None = None, has_linkedin: bool | None = None):
        query = select(Company).where(Company.organization_id == organization_id).order_by(Company.id)
        if company_id is not None:
            query = query.where(Company.id == company_id)
        companies = list(db.scalars(query).all())
        items = []
        relevance_order = {DecisionMakerRelevance.HIGH: 3, DecisionMakerRelevance.MEDIUM: 2, DecisionMakerRelevance.LOW: 1}
        for company in companies:
            assessment = self.assess_company(db, company.id, organization_id)
            for contact in assessment["contacts"]:
                if minimum_relevance and relevance_order[contact.relevance] < relevance_order[minimum_relevance]:
                    continue
                if has_email is not None and contact.contact_methods["has_email"] != has_email:
                    continue
                if has_phone is not None and contact.contact_methods["has_phone"] != has_phone:
                    continue
                if has_linkedin is not None and contact.contact_methods["has_linkedin"] != has_linkedin:
                    continue
                items.append(DecisionMakerQueueItemResponse(company_name=company.company_name, assessment=contact))
        items.sort(key=lambda item: (-relevance_order[item.assessment.relevance], -item.assessment.company_prospect_score, -item.assessment.relevance_score, -sum(item.assessment.contact_methods.values()), item.company_name.lower(), (item.assessment.contact.full_name or "").lower(), item.assessment.contact.id))
        return DecisionMakerQueueResponse(items=items, total=len(items), human_review_required=True)