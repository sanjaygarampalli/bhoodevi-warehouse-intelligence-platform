from datetime import datetime
from urllib.parse import urlparse

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.company import Company
from app.models.company_intelligence import *
from app.models.market_signal import MarketSignal, MarketSignalStatus
from app.services.company_prospect_priority import CompanyProspectPriorityService


class CompanyIntelligenceError(Exception):
    pass


class CompanyIntelligenceNotFound(CompanyIntelligenceError):
    pass


class CompanyWarehouseProfileNotFound(CompanyIntelligenceError):
    pass


class CompanyContactNotFound(CompanyIntelligenceError):
    pass


class CompanyContactMethodNotFound(CompanyIntelligenceError):
    pass


class CompanyIntelligenceOrganizationError(CompanyIntelligenceError):
    pass


class DuplicateIntelligenceProfile(CompanyIntelligenceError):
    pass


class DuplicateContactMethod(CompanyIntelligenceError):
    pass


class InvalidContactMethodValue(CompanyIntelligenceError):
    pass


class CompanyIntelligenceService:
    @staticmethod
    def _commit(db: Session):
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    def company(self, db: Session, company_id: int) -> Company:
        company = db.get(Company, company_id)
        if company is None:
            raise CompanyIntelligenceNotFound("Company not found")
        return company

    def scoped_company(self, db: Session, company_id: int, organization_id: int) -> Company:
        company = db.scalar(select(Company).where(Company.id == company_id, Company.organization_id == organization_id))
        if company is None:
            raise CompanyIntelligenceOrganizationError("Company is not accessible in this organization")
        return company

    @staticmethod
    def _normalize(value: str, method_type: ContactMethodType) -> str:
        if method_type in {ContactMethodType.EMAIL, ContactMethodType.LINKEDIN, ContactMethodType.WEBSITE}:
            return value.strip().lower()
        return "".join(value.split())

    @staticmethod
    def _validate_method_value(value: str, method_type: ContactMethodType) -> None:
        try:
            if method_type == ContactMethodType.EMAIL:
                TypeAdapter(EmailStr).validate_python(value)
            elif method_type in {ContactMethodType.LINKEDIN, ContactMethodType.WEBSITE}:
                parsed = urlparse(value)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError("URL must use HTTP or HTTPS")
                if method_type == ContactMethodType.LINKEDIN:
                    hostname = (parsed.hostname or "").lower().rstrip(".")
                    if hostname != "linkedin.com" and not hostname.endswith(".linkedin.com"):
                        raise ValueError("LinkedIn URL must use a linkedin.com host")
        except (ValidationError, ValueError) as exc:
            raise InvalidContactMethodValue(f"Invalid {method_type.value.lower()} contact method value") from exc

    def get_profile(self, db: Session, company_id: int, organization_id: int):
        self.scoped_company(db, company_id, organization_id)
        return db.scalar(select(CompanyIntelligenceProfile).where(CompanyIntelligenceProfile.company_id == company_id, CompanyIntelligenceProfile.organization_id == organization_id))

    def create_profile(self, db: Session, company_id: int, organization_id: int, data):
        self.scoped_company(db, company_id, organization_id)
        profile = CompanyIntelligenceProfile(company_id=company_id, organization_id=organization_id, **data.model_dump())
        db.add(profile)
        try:
            self._commit(db)
        except IntegrityError as exc:
            db.rollback()
            raise DuplicateIntelligenceProfile("Intelligence profile already exists") from exc
        db.refresh(profile)
        return profile

    def update_profile(self, db: Session, company_id: int, organization_id: int, data):
        self.scoped_company(db, company_id, organization_id)
        profile = db.scalar(select(CompanyIntelligenceProfile).where(CompanyIntelligenceProfile.company_id == company_id, CompanyIntelligenceProfile.organization_id == organization_id))
        if profile is None:
            raise CompanyIntelligenceNotFound("Intelligence profile not found")
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)
        self._commit(db)
        db.refresh(profile)
        return profile

    def get_warehouse(self, db: Session, company_id: int, organization_id: int):
        self.scoped_company(db, company_id, organization_id)
        profile = db.scalar(select(CompanyWarehouseProfile).where(CompanyWarehouseProfile.company_id == company_id, CompanyWarehouseProfile.organization_id == organization_id).options(selectinload(CompanyWarehouseProfile.use_cases)))
        if profile is None:
            raise CompanyWarehouseProfileNotFound("Warehouse profile not found")
        return profile

    def save_warehouse(self, db: Session, company_id: int, organization_id: int, data, create: bool = False):
        self.scoped_company(db, company_id, organization_id)
        profile = db.scalar(select(CompanyWarehouseProfile).where(CompanyWarehouseProfile.company_id == company_id, CompanyWarehouseProfile.organization_id == organization_id).options(selectinload(CompanyWarehouseProfile.use_cases)))
        if create and profile is not None:
            raise DuplicateIntelligenceProfile("Warehouse profile already exists")
        if profile is None:
            profile = CompanyWarehouseProfile(company_id=company_id, organization_id=organization_id)
            db.add(profile)
            db.flush()
        values = data.model_dump(exclude_unset=True) if not create else data.model_dump()
        use_cases = values.pop("use_cases", None)
        for key, value in values.items():
            setattr(profile, key, value)
        if use_cases is not None:
            profile.use_cases = [CompanyWarehouseUseCase(use_case=value) for value in dict.fromkeys(use_cases)]
        self._commit(db)
        return self.get_warehouse(db, company_id, organization_id)

    def add_contact(self, db: Session, company_id: int, organization_id: int, data):
        self.scoped_company(db, company_id, organization_id)
        contact = CompanyContact(company_id=company_id, organization_id=organization_id, **data.model_dump())
        db.add(contact)
        self._commit(db)
        db.refresh(contact)
        self.recalc_contact(db, contact, commit=True)
        return self.get_contact(db, contact.id, organization_id)

    def get_contact(self, db: Session, contact_id: int, organization_id: int):
        contact = db.scalar(select(CompanyContact).where(CompanyContact.id == contact_id, CompanyContact.organization_id == organization_id).options(selectinload(CompanyContact.methods)))
        if contact is None:
            raise CompanyContactNotFound("Contact not found")
        return contact

    def update_contact(self, db: Session, contact_id: int, organization_id: int, data):
        contact = self.get_contact(db, contact_id, organization_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(contact, key, value)
        self._commit(db)
        self.recalc_contact(db, contact, commit=True)
        return self.get_contact(db, contact_id, organization_id)

    def list_contacts(self, db: Session, company_id: int, organization_id: int, page: int, page_size: int, search: str | None = None, job_title: str | None = None, department=None, seniority=None, verification_status=None, has_linkedin: bool | None = None):
        self.scoped_company(db, company_id, organization_id)
        base = select(CompanyContact).where(CompanyContact.company_id == company_id, CompanyContact.organization_id == organization_id)
        if search:
            term = f"%{search.strip()}%"
            base = base.where(or_(CompanyContact.full_name.ilike(term), CompanyContact.first_name.ilike(term), CompanyContact.last_name.ilike(term), CompanyContact.job_title.ilike(term)))
        if job_title:
            base = base.where(CompanyContact.job_title.ilike(f"%{job_title.strip()}%"))
        if department is not None:
            base = base.where(CompanyContact.department == department)
        if seniority is not None:
            base = base.where(CompanyContact.seniority == seniority)
        if verification_status is not None:
            base = base.join(CompanyContactMethod).where(CompanyContactMethod.verification_status == verification_status)
        if has_linkedin is True:
            base = base.join(CompanyContactMethod).where(CompanyContactMethod.method_type == ContactMethodType.LINKEDIN)
        if has_linkedin is False:
            base = base.where(~CompanyContact.methods.any(CompanyContactMethod.method_type == ContactMethodType.LINKEDIN))
        base = base.distinct()
        total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
        items = list(db.scalars(base.options(selectinload(CompanyContact.methods)).order_by(CompanyContact.id).offset((page - 1) * page_size).limit(page_size)).all())
        return items, total

    def contact_intelligence(self, db: Session, company_id: int, organization_id: int):
        self.scoped_company(db, company_id, organization_id)
        contacts, _ = self.list_contacts(db, company_id, organization_id, 1, 100)
        company_priority = CompanyProspectPriorityService().assess(db, company_id)
        prospect_score = company_priority.priority_score if company_priority else 0
        ranked = []
        for contact in contacts:
            score, reasons = self.contact_priority(contact, prospect_score)
            ranked.append((score, contact.id, contact, reasons))
        ranked.sort(key=lambda item: (-item[0], item[2].full_name or "", item[1]))
        items = [{"contact": contact, "rank": rank, "priority_score": score, "company_prospect_score": prospect_score, "reasons": reasons, "human_review_required": True} for rank, (score, _, contact, reasons) in enumerate(ranked, 1)]
        verified_count = sum(any(method.verification_status == VerificationStatus.VERIFIED for method in contact.methods) for contact in contacts)
        missing = []
        if not contacts:
            missing.append("No structured company contacts are recorded.")
        if not any(any(method.method_type == ContactMethodType.EMAIL for method in contact.methods) for contact in contacts):
            missing.append("No business email is recorded.")
        if not any(any(method.method_type == ContactMethodType.LINKEDIN for method in contact.methods) for contact in contacts):
            missing.append("No LinkedIn profile is recorded.")
        return {"company_id": company_id, "organization_id": organization_id, "contacts": items, "total": len(items), "verified_contact_count": verified_count, "missing_intelligence": missing, "recommended_next_step": "Human review of the highest-ranked contact and verification gaps."}

    def add_method(self, db: Session, contact_id: int, organization_id: int, data):
        contact = self.get_contact(db, contact_id, organization_id)
        self._validate_method_value(data.value, data.method_type)
        normalized_value = self._normalize(data.value, data.method_type)
        duplicate = db.scalar(
            select(CompanyContactMethod)
            .join(CompanyContact)
            .where(
                CompanyContact.organization_id == organization_id,
                CompanyContact.company_id == contact.company_id,
                CompanyContactMethod.method_type == data.method_type,
                CompanyContactMethod.normalized_value == normalized_value,
                CompanyContactMethod.contact_id != contact.id,
            )
        )
        if duplicate is not None:
            raise DuplicateContactMethod("Contact identity already exists for this company")
        if data.is_primary:
            db.execute(update(CompanyContactMethod).where(CompanyContactMethod.contact_id == contact.id).values(is_primary=False))
        method = CompanyContactMethod(contact_id=contact.id, normalized_value=normalized_value, **data.model_dump())
        db.add(method)
        try:
            self._commit(db)
        except IntegrityError as exc:
            db.rollback()
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            if constraint in {None, "uq_company_contact_method"}:
                raise DuplicateContactMethod("Duplicate contact method") from exc
            raise
        db.refresh(method)
        return method

    def get_method(self, db: Session, method_id: int, organization_id: int):
        method = db.scalar(select(CompanyContactMethod).join(CompanyContact).where(CompanyContactMethod.id == method_id, CompanyContact.organization_id == organization_id))
        if method is None:
            raise CompanyContactMethodNotFound("Contact method not found")
        return method

    def update_method(self, db: Session, method_id: int, organization_id: int, data):
        method = self.get_method(db, method_id, organization_id)
        values = data.model_dump(exclude_unset=True)
        if method.verification_status == VerificationStatus.VERIFIED:
            changing_value = "value" in values and values["value"] != method.value
            weakening_verification = values.get("is_verified") is False or (
                values.get("verification_status") is not None
                and values["verification_status"] != VerificationStatus.VERIFIED
            )
            explicit_verified_correction = (
                values.get("is_verified") is True
                and values.get("verification_status") == VerificationStatus.VERIFIED
            )
            if (changing_value and not explicit_verified_correction) or weakening_verification:
                raise InvalidContactMethodValue(
                    "Verified contact methods require an explicit verified correction"
                )
        if "value" in values:
            self._validate_method_value(values["value"], method.method_type)
            normalized_value = self._normalize(values["value"], method.method_type)
            duplicate = db.scalar(
                select(CompanyContactMethod)
                .join(CompanyContact)
                .where(
                    CompanyContact.organization_id == organization_id,
                    CompanyContactMethod.method_type == method.method_type,
                    CompanyContactMethod.normalized_value == normalized_value,
                    CompanyContactMethod.id != method.id,
                )
            )
            if duplicate is not None:
                raise DuplicateContactMethod("Contact identity already exists for this organization")
            method.value = values.pop("value")
            method.normalized_value = normalized_value
        if values.get("is_primary") is True:
            db.execute(update(CompanyContactMethod).where(CompanyContactMethod.contact_id == method.contact_id, CompanyContactMethod.id != method.id).values(is_primary=False))
        if values.get("is_verified") is True:
            values.setdefault("verification_status", VerificationStatus.VERIFIED)
        elif values.get("is_verified") is False:
            values.setdefault("verification_status", VerificationStatus.UNVERIFIED)
        if values.get("verification_status") == VerificationStatus.VERIFIED:
            values["is_verified"] = True
        elif values.get("verification_status") is not None:
            values["is_verified"] = False
        for key, value in values.items():
            setattr(method, key, value)
        self._commit(db)
        db.refresh(method)
        return method

    @staticmethod
    def contact_quality(contact):
        score = 0
        reasons = []
        if contact.seniority in {ContactSeniority.OWNER, ContactSeniority.FOUNDER, ContactSeniority.C_LEVEL, ContactSeniority.VP, ContactSeniority.DIRECTOR}:
            score += 40
            reasons.append("Relevant seniority")
        if contact.department in {ContactDepartment.LOGISTICS, ContactDepartment.SUPPLY_CHAIN, ContactDepartment.WAREHOUSE, ContactDepartment.OPERATIONS}:
            score += 25
            reasons.append("Warehouse-related department")
        if contact.is_primary:
            score += 15
            reasons.append("Primary contact")
        verified = sum(method.verification_status == VerificationStatus.VERIFIED for method in contact.methods)
        score += min(verified * 20, 20)
        if verified:
            reasons.append("Verified contact method")
        return min(score, 100), {"score": min(score, 100), "reasons": reasons}

    @staticmethod
    def contact_priority(contact, company_prospect_score: int):
        score = 0
        reasons = []
        title = (contact.job_title or "").lower()
        relevant_terms = ("founder", "owner", "ceo", "managing director", "director", "head", "chief", "operations", "supply chain", "logistics", "warehouse", "procurement")
        if any(term in title for term in relevant_terms):
            score += 35
            reasons.append("Designation contains a warehouse-relevant leadership or operations role.")
        if contact.seniority in {ContactSeniority.OWNER, ContactSeniority.FOUNDER, ContactSeniority.C_LEVEL, ContactSeniority.VP, ContactSeniority.DIRECTOR, ContactSeniority.HEAD}:
            score += 25
            reasons.append("Senior professional level increases investigation relevance.")
        if contact.department in {ContactDepartment.LOGISTICS, ContactDepartment.SUPPLY_CHAIN, ContactDepartment.WAREHOUSE, ContactDepartment.OPERATIONS, ContactDepartment.PROCUREMENT}:
            score += 20
            reasons.append("Department is relevant to warehouse or logistics decisions.")
        verified = any(method.verification_status == VerificationStatus.VERIFIED for method in contact.methods)
        if verified:
            score += 10
            reasons.append("At least one contact method is verified.")
        if any(method.method_type == ContactMethodType.EMAIL for method in contact.methods):
            score += 5
            reasons.append("Business email is available.")
        if any(method.method_type == ContactMethodType.LINKEDIN for method in contact.methods):
            score += 5
            reasons.append("LinkedIn profile is available.")
        if company_prospect_score >= 50:
            reasons.append("Company prospect priority supports human investigation.")
        return min(score, 100), reasons

    def recalc_contact(self, db: Session, contact, commit: bool = True):
        score, explanation = self.contact_quality(contact)
        contact.contact_quality_score = score
        contact.contact_quality_explanation = explanation
        if commit:
            self._commit(db)
        return contact

    def get_icp(self, db: Session, company_id: int, organization_id: int):
        self.scoped_company(db, company_id, organization_id)
        return db.scalar(select(CompanyICPAssessment).where(CompanyICPAssessment.company_id == company_id, CompanyICPAssessment.organization_id == organization_id))

    def recalculate_icp(self, db: Session, company_id: int, organization_id: int):
        self.scoped_company(db, company_id, organization_id)
        profile = self.get_profile(db, company_id, organization_id)
        signals = db.scalar(select(func.count()).select_from(MarketSignal).where(MarketSignal.company_id == company_id, MarketSignal.organization_id == organization_id, MarketSignal.status == MarketSignalStatus.VERIFIED)) or 0
        factors = [{"name": "Industry profile", "impact": 35 if profile and profile.industry else 0}, {"name": "Expansion indicators", "impact": 35 if profile and any([profile.is_expanding, profile.is_hiring, profile.is_raising_capacity, profile.is_opening_new_facility]) else 0}, {"name": "Verified market signals", "impact": min(signals * 10, 30)}]
        score = min(sum(item["impact"] for item in factors), 100)
        classification = IcpClassification.EXCELLENT if score >= 80 else IcpClassification.GOOD if score >= 60 else IcpClassification.MODERATE if score >= 40 else IcpClassification.LOW if score >= 20 else IcpClassification.POOR
        assessment = self.get_icp(db, company_id, organization_id) or CompanyICPAssessment(company_id=company_id, organization_id=organization_id)
        assessment.score, assessment.classification, assessment.factors, assessment.calculated_at = score, classification, factors, datetime.utcnow()
        db.add(assessment)
        self._commit(db)
        return assessment

    def get_opportunity(self, db: Session, company_id: int, organization_id: int):
        self.scoped_company(db, company_id, organization_id)
        return db.scalar(select(CompanyOpportunityAssessment).where(CompanyOpportunityAssessment.company_id == company_id, CompanyOpportunityAssessment.organization_id == organization_id))

    def recalculate_opportunity(self, db: Session, company_id: int, organization_id: int):
        company = self.scoped_company(db, company_id, organization_id)
        icp = self.get_icp(db, company_id, organization_id)
        if icp is None:
            icp = self.recalculate_icp(db, company_id, organization_id)
        warehouse = db.scalar(select(CompanyWarehouseProfile).where(CompanyWarehouseProfile.company_id == company_id, CompanyWarehouseProfile.organization_id == organization_id))
        contacts = list(db.scalars(select(CompanyContact).where(CompanyContact.company_id == company_id, CompanyContact.organization_id == organization_id).options(selectinload(CompanyContact.methods))).all())
        for contact in contacts:
            self.recalc_contact(db, contact, commit=False)
        fit = {WarehouseDependency.VERY_HIGH: 100, WarehouseDependency.HIGH: 85, WarehouseDependency.MEDIUM: 60, WarehouseDependency.LOW: 25, WarehouseDependency.UNKNOWN: 0}.get(warehouse.warehouse_dependency if warehouse else WarehouseDependency.UNKNOWN, 0)
        verified = db.scalar(select(func.count()).select_from(MarketSignal).where(MarketSignal.company_id == company_id, MarketSignal.organization_id == organization_id, MarketSignal.status == MarketSignalStatus.VERIFIED)) or 0
        demand = min(100, verified * 35)
        geo = 100 if (company.headquarters_country or "India") in {"India", "IN"} else 30
        contact_score = max((contact.contact_quality_score for contact in contacts), default=0)
        score = round(icp.score * .30 + fit * .25 + demand * .20 + geo * .10 + contact_score * .15)
        priority = OpportunityPriority.CRITICAL if score >= 80 else OpportunityPriority.HIGH if score >= 60 else OpportunityPriority.MEDIUM if score >= 35 else OpportunityPriority.LOW
        explanation = {"factors": [{"name": "ICP Fit", "impact": icp.score}, {"name": "Warehouse Fit", "impact": fit}, {"name": "Demand Signals", "impact": demand, "verified_count": verified}, {"name": "Geographic Fit", "impact": geo}, {"name": "Contact Availability", "impact": contact_score}], "formula": "30% ICP + 25% warehouse fit + 20% verified demand + 10% geography + 15% contact"}
        assessment = self.get_opportunity(db, company_id, organization_id) or CompanyOpportunityAssessment(company_id=company_id, organization_id=organization_id)
        assessment.overall_score, assessment.priority, assessment.warehouse_fit_score, assessment.demand_score, assessment.geographic_score, assessment.contact_score, assessment.explanation, assessment.calculated_at = score, priority, fit, demand, geo, contact_score, explanation, datetime.utcnow()
        db.add(assessment)
        self._commit(db)
        return assessment

    def get_next_action(self, db: Session, company_id: int, organization_id: int):
        self.scoped_company(db, company_id, organization_id)
        return db.scalar(select(CompanyNextBestAction).where(CompanyNextBestAction.company_id == company_id, CompanyNextBestAction.organization_id == organization_id))

    def recalculate_next_action(self, db: Session, company_id: int, organization_id: int):
        assessment = self.get_opportunity(db, company_id, organization_id)
        if assessment is None:
            raise CompanyIntelligenceNotFound("Opportunity assessment not found; recalculate it first")
        contacts = list(db.scalars(select(CompanyContact).where(CompanyContact.company_id == company_id, CompanyContact.organization_id == organization_id).options(selectinload(CompanyContact.methods))).all())
        verified = any(method.verification_status == VerificationStatus.VERIFIED for contact in contacts for method in contact.methods)
        if assessment.priority == OpportunityPriority.LOW:
            action, reason = NextBestActionType.NO_ACTION, "Low warehouse fit or priority"
        elif assessment.priority in {OpportunityPriority.CRITICAL, OpportunityPriority.HIGH} and verified:
            action, reason = NextBestActionType.CONTACT_IMMEDIATELY, "High operational priority with verified contact"
        elif assessment.priority in {OpportunityPriority.CRITICAL, OpportunityPriority.HIGH}:
            action, reason = NextBestActionType.FIND_DECISION_MAKER, "High operational priority but no verified contact"
        elif assessment.contact_score == 0:
            action, reason = NextBestActionType.RESEARCH_COMPANY, "Good opportunity evidence but insufficient contact evidence"
        else:
            action, reason = NextBestActionType.MONITOR_EXPANSION, "Monitor recorded expansion and demand evidence"
        row = self.get_next_action(db, company_id, organization_id) or CompanyNextBestAction(company_id=company_id, organization_id=organization_id)
        row.action, row.reason, row.calculated_at = action, reason, datetime.utcnow()
        db.add(row)
        self._commit(db)
        return row

    def summary(self, db: Session, company_id: int, organization_id: int):
        company = self.scoped_company(db, company_id, organization_id)
        return {"company": company, "intelligence_profile": self.get_profile(db, company_id, organization_id), "warehouse_profile": db.scalar(select(CompanyWarehouseProfile).where(CompanyWarehouseProfile.company_id == company_id, CompanyWarehouseProfile.organization_id == organization_id).options(selectinload(CompanyWarehouseProfile.use_cases))), "contacts": list(db.scalars(select(CompanyContact).where(CompanyContact.company_id == company_id, CompanyContact.organization_id == organization_id).options(selectinload(CompanyContact.methods))).all()), "icp_assessment": self.get_icp(db, company_id, organization_id), "opportunity_assessment": self.get_opportunity(db, company_id, organization_id), "next_best_action": self.get_next_action(db, company_id, organization_id)}