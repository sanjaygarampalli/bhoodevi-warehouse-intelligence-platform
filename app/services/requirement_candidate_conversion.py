from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.lead import LeadSource
from app.models.market_signal import MarketSignal, RequirementCandidate, RequirementCandidateStatus
from app.models.requirement_candidate_conversion import (
    RequirementCandidateConversion,
    RequirementCandidateConversionStatus,
)
from app.models.organization_membership import MembershipStatus, OrganizationMembership
from app.models.user import User
from app.services.organization_access import WRITE_ROLES
from app.repositories.requirement_candidate_conversion import RequirementCandidateConversionRepository
from app.schemas.lead import LeadCreate
from app.schemas.requirement import RequirementCreate
from app.schemas.requirement_candidate_conversion import RequirementCandidateConversionRequest
from app.services.lead import LeadService
from app.services.requirement import RequirementService


class RequirementCandidateConversionError(ValueError):
    pass


class RequirementCandidateConversionService:
    def __init__(self):
        self.repository = RequirementCandidateConversionRepository()
        self.leads = LeadService()
        self.requirements = RequirementService()

    def convert(self, db: Session, candidate_id: int, payload: RequirementCandidateConversionRequest, *, user_id: int, organization_id: int):
        candidate = db.scalar(select(RequirementCandidate).where(RequirementCandidate.id == candidate_id).with_for_update())
        if candidate is None:
            raise LookupError("Requirement candidate not found")
        if candidate.organization_id != organization_id:
            raise RequirementCandidateConversionError("Requirement candidate does not belong to the requested organization")

        company = db.get(Company, candidate.company_id)
        signal = db.get(MarketSignal, candidate.market_signal_id)
        if company is None or company.organization_id != organization_id or signal is None or signal.organization_id != organization_id:
            raise RequirementCandidateConversionError("Requirement candidate ownership is invalid")

        existing = self.repository.get_by_candidate(db, candidate.id, lock=True)
        if existing is not None:
            if existing.status == RequirementCandidateConversionStatus.CONVERTED:
                return existing, existing.company, existing.lead, existing.requirement, False
            raise RequirementCandidateConversionError("Requirement candidate already has a conversion in progress or failed")
        if candidate.status != RequirementCandidateStatus.ACCEPTED:
            raise RequirementCandidateConversionError("Requirement candidate is not eligible for conversion")
        if payload.owner_user_id is not None:
            owner = db.get(User, payload.owner_user_id)
            membership = db.scalar(select(OrganizationMembership).where(
                OrganizationMembership.user_id == payload.owner_user_id,
                OrganizationMembership.organization_id == candidate.organization_id,
                OrganizationMembership.status == MembershipStatus.ACTIVE,
                OrganizationMembership.role.in_(WRITE_ROLES),
            ))
            if owner is None:
                raise RequirementCandidateConversionError("Lead owner not found")
            if membership is None:
                raise RequirementCandidateConversionError(
                    "Lead owner must have an active organization membership with write access"
                )

        conversion = RequirementCandidateConversion(
            organization_id=organization_id,
            requirement_candidate_id=candidate.id,
            company_id=company.id,
            status=RequirementCandidateConversionStatus.PENDING,
            created_by_user_id=user_id,
        )
        try:
            self.repository.create_pending(db, conversion)
            lead = self.leads.create_lead_in_transaction(db, LeadCreate(
                lead_number=payload.lead_number,
                company_id=company.id,
                lead_source=LeadSource.AI_DISCOVERY,
                space_needed_sqft=payload.space_needed_sqft,
                requirement_type=payload.requirement_type,
                target_industry=company.industry,
                preferred_city=candidate.city,
                preferred_state=candidate.state,
                preferred_country=candidate.country,
                expected_monthly_rent=payload.expected_monthly_rent,
                currency=payload.currency,
                move_in_timeframe=payload.move_in_timeframe,
                lease_tenure_years=payload.lease_tenure_years,
                owner_user_id=payload.owner_user_id,
                priority=payload.priority,
            ))
            if lead is None:
                raise RequirementCandidateConversionError("Lead could not be created")
            description = payload.requirement_description or candidate.reasoning
            if signal.title:
                description = f"Source signal: {signal.title}\n\n{description}"
            requirement = self.requirements.create_requirement_in_transaction(db, RequirementCreate(
                lead_id=lead.id,
                title=payload.requirement_title or candidate.summary,
                description=description,
                industry=company.industry,
                preferred_city=candidate.city,
                preferred_state=candidate.state,
                preferred_locality=candidate.district,
                required_builtup_area=payload.required_builtup_area,
                minimum_area=payload.minimum_area,
                maximum_area=payload.maximum_area,
                warehouse_type=payload.warehouse_type,
                lease_duration_months=payload.lease_duration_months,
                requirement_status=payload.requirement_status,
            ))
            if requirement is None:
                raise RequirementCandidateConversionError("Requirement could not be created")
            conversion.lead_id = lead.id
            conversion.requirement_id = requirement.id
            conversion.status = RequirementCandidateConversionStatus.CONVERTED
            conversion.converted_at = datetime.now(timezone.utc)
            candidate.status = RequirementCandidateStatus.CONVERTED
            db.commit()
            db.refresh(conversion)
            db.refresh(company)
            db.refresh(lead)
            db.refresh(requirement)
            return conversion, company, lead, requirement, True
        except Exception as exc:
            db.rollback()
            if isinstance(exc, (RequirementCandidateConversionError, LookupError)):
                raise
            raise RequirementCandidateConversionError("Requirement candidate conversion failed") from exc