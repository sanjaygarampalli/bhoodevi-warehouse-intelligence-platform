from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.lead import Lead
from app.models.requirement import Requirement
from app.models.requirement_intelligence import (
    RequirementEvidenceClassification,
    RequirementEvidenceVerificationStatus,
    RequirementFreshness,
    RequirementIntelligenceAssessment,
    RequirementIntelligenceEvidence,
)
from app.models.user import User
from app.models.market_signal import RequirementCandidate
from app.models.requirement_candidate_conversion import RequirementCandidateConversion, RequirementCandidateConversionStatus
from app.schemas.requirement_intelligence import RequirementEvidenceCreate, RequirementEvidenceUpdate
from app.schemas.requirement_intelligence import RequirementAssessmentResponse


class RequirementIntelligenceNotFound(LookupError):
    pass


class RequirementEvidenceConflict(ValueError):
    pass


class RequirementIntelligenceService:
    def get_requirement(self, db: Session, requirement_id: int) -> Requirement | None:
        return db.get(Requirement, requirement_id)

    def organization_id(self, db: Session, requirement_id: int) -> int | None:
        return db.scalar(
            select(Company.organization_id)
            .join(Lead, Lead.company_id == Company.id)
            .join(Requirement, Requirement.lead_id == Lead.id)
            .where(Requirement.id == requirement_id)
        )

    def list_requirements(self, db: Session, organization_id: int, *, status=None, query: str | None = None, limit: int = 100, offset: int = 0):
        statement = (
            select(Requirement)
            .join(Lead, Lead.id == Requirement.lead_id)
            .join(Company, Company.id == Lead.company_id)
            .where(Company.organization_id == organization_id)
            .order_by(Requirement.updated_at.desc(), Requirement.id.desc())
        )
        if status is not None:
            statement = statement.where(Requirement.requirement_status == status)
        if query:
            pattern = f"%{query.strip()}%"
            statement = statement.where(Requirement.title.ilike(pattern))
        return list(db.scalars(statement.limit(limit).offset(offset)).all())

    def company_for(self, db: Session, requirement: Requirement) -> Company:
        company = db.scalar(select(Company).join(Lead, Lead.company_id == Company.id).where(Lead.id == requirement.lead_id))
        if company is None:
            raise RequirementIntelligenceNotFound("Requirement company not found")
        return company

    def evidence(self, db: Session, requirement_id: int):
        return list(db.scalars(select(RequirementIntelligenceEvidence).where(
            RequirementIntelligenceEvidence.requirement_id == requirement_id,
        ).order_by(RequirementIntelligenceEvidence.evidence_date.desc().nullslast(), RequirementIntelligenceEvidence.id.desc())).all())

    def create_evidence(self, db: Session, requirement: Requirement, data: RequirementEvidenceCreate):
        if data.verification_status == RequirementEvidenceVerificationStatus.VERIFIED:
            raise RequirementEvidenceConflict("New evidence must be reviewed before it can be verified")
        evidence = RequirementIntelligenceEvidence(
            organization_id=self.organization_id(db, requirement.id),
            requirement_id=requirement.id,
            **data.model_dump(),
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        return evidence

    def update_evidence(self, db: Session, evidence: RequirementIntelligenceEvidence, data: RequirementEvidenceUpdate, user: User):
        # Re-read under a row lock: a request may have loaded an unverified
        # record before another transaction completed verification.
        evidence = db.scalar(select(RequirementIntelligenceEvidence).where(
            RequirementIntelligenceEvidence.id == evidence.id,
        ).with_for_update().execution_options(populate_existing=True))
        if evidence is None:
            raise RequirementIntelligenceNotFound("Requirement evidence not found")
        values = data.model_dump(exclude_unset=True)
        substantive = {"source", "source_type", "source_url", "observed_evidence", "inference", "classification", "evidence_date", "confidence"}
        if (evidence.verified_at is not None or evidence.verification_status == RequirementEvidenceVerificationStatus.VERIFIED) and substantive.intersection(values):
            raise RequirementEvidenceConflict("Verified evidence is protected from substantive edits")
        target_status = values.get("verification_status")
        if evidence.verified_at is not None and target_status not in (None, RequirementEvidenceVerificationStatus.VERIFIED, RequirementEvidenceVerificationStatus.REJECTED):
            raise RequirementEvidenceConflict("Previously verified evidence cannot be reopened; record replacement evidence")
        if target_status == RequirementEvidenceVerificationStatus.VERIFIED:
            if evidence.verification_status not in (RequirementEvidenceVerificationStatus.REVIEWED, RequirementEvidenceVerificationStatus.VERIFIED):
                raise RequirementEvidenceConflict("Evidence must be reviewed before verification")
            if evidence.verified_at is None:
                evidence.verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
                evidence.verified_by_user_id = user.id
        for key, value in values.items():
            setattr(evidence, key, value)
        db.commit()
        db.refresh(evidence)
        return evidence

    def assessment(self, db: Session, requirement: Requirement):
        evidence = [item for item in self.evidence(db, requirement.id)
                    if item.verification_status != RequirementEvidenceVerificationStatus.REJECTED]
        verified = [item for item in evidence if item.verification_status == RequirementEvidenceVerificationStatus.VERIFIED]
        dates = [item.evidence_date.replace(tzinfo=timezone.utc) if item.evidence_date.tzinfo is None else item.evidence_date.astimezone(timezone.utc) for item in evidence if item.evidence_date is not None]
        anchor = max(dates) if dates else None
        if anchor is None:
            freshness = RequirementFreshness.UNKNOWN
        elif anchor >= datetime.now(timezone.utc) - timedelta(days=30):
            freshness = RequirementFreshness.FRESH
        elif anchor >= datetime.now(timezone.utc) - timedelta(days=90):
            freshness = RequirementFreshness.AGING
        else:
            freshness = RequirementFreshness.STALE

        def confidence(value) -> Decimal | None:
            return Decimal("100") if value is not None else None

        dimensions = {
            "geography_confidence": confidence(requirement.preferred_city or requirement.preferred_state),
            "size_confidence": confidence(requirement.minimum_area or requirement.maximum_area or requirement.required_builtup_area),
            "timing_confidence": confidence(requirement.move_in_timeframe),
            "operational_confidence": confidence(requirement.warehouse_type or requirement.required_docks or requirement.required_clear_height),
            "commercial_confidence": confidence(requirement.budget_per_sqft or requirement.lease_duration_months),
        }
        known = [value for value in dimensions.values() if value is not None]
        evidence_strength = Decimal(str(round((len(verified) / len(evidence)) * 100, 2))) if evidence else Decimal("0")
        reasons = ["Verified evidence supports this requirement." if verified else "No verified requirement-specific evidence is present."]
        if freshness == RequirementFreshness.UNKNOWN:
            reasons.append("Freshness is unknown because no evidence date is available.")
        elif freshness == RequirementFreshness.STALE:
            reasons.append("The latest evidence is more than 90 days old.")
        elif len(known) < len(dimensions):
            reasons.append("Some qualification dimensions remain unknown because structured demand fields are incomplete.")
        # Field presence is completeness, never proof of a factual demand claim.
        # Without dimension-level evidence links we cannot assert confidence in
        # geography, size, timing, operations or commercial terms.
        dimensions = {key: None for key in dimensions}
        requirement_confidence = None
        reasons.append("Structured field presence does not establish evidence-backed confidence; dimension provenance is not recorded.")
        values = dict(
            organization_id=self.organization_id(db, requirement.id), requirement_id=requirement.id,
            requirement_confidence=requirement_confidence, evidence_strength=evidence_strength,
            freshness=freshness, freshness_anchor=anchor.replace(tzinfo=None) if anchor else None, reasons=reasons,
            calculated_at=datetime.now(timezone.utc).replace(tzinfo=None), **dimensions,
        )
        # Live GET assessments do not persist, commit caller changes or race on
        # the unique requirement assessment row. Persisted history is separate.
        return RequirementAssessmentResponse(id=None, **values)

    def market_signal_ids(self, db: Session, requirement_id: int) -> list[int]:
        """Follow the persisted conversion link; never infer from company identity."""
        organization_id = self.organization_id(db, requirement_id)
        return list(db.scalars(select(RequirementCandidate.market_signal_id)
            .join(RequirementCandidateConversion,
                  RequirementCandidateConversion.requirement_candidate_id == RequirementCandidate.id)
            .where(RequirementCandidateConversion.requirement_id == requirement_id,
                   RequirementCandidateConversion.organization_id == organization_id,
                   RequirementCandidate.organization_id == organization_id,
                   RequirementCandidateConversion.status == RequirementCandidateConversionStatus.CONVERTED)
            .distinct()).all())
