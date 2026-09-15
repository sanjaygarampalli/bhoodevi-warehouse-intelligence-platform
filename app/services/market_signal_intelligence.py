from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.market_signal import (
    DemandStrength,
    EvidenceCredibility,
    MarketSignal,
    MarketSignalConfidence,
    MarketSignalEvidence,
    MarketSignalStatus,
    MarketSignalType,
    RequirementCandidate,
    RequirementCandidateStatus,
)
from app.models.company import Company
from app.models.user import User
from app.schemas.market_signal import (
    MarketSignalAssessmentResponse,
    MarketSignalCreate,
    MarketSignalEvidenceCreate,
    MarketSignalEvidenceUpdate,
    MarketSignalUpdate,
    RequirementCandidateUpdate,
)


class MarketSignalError(Exception):
    """Base exception for Market Signal domain errors."""


class MarketSignalNotFound(MarketSignalError):
    pass


class MarketSignalConflict(MarketSignalError):
    pass


class EvidenceNotFound(MarketSignalError):
    pass


class RequirementCandidateNotFound(MarketSignalError):
    pass


class InvalidStatusTransition(MarketSignalError):
    pass


class CandidateAlreadyExists(MarketSignalConflict):
    pass


class CandidateNotEligible(MarketSignalError):
    pass


class InvalidCompanyOrganization(MarketSignalError):
    pass


class MarketSignalIntelligenceService:
    signal_transitions = {
        MarketSignalStatus.DETECTED: {
            MarketSignalStatus.UNDER_REVIEW,
            MarketSignalStatus.ARCHIVED,
        },
        MarketSignalStatus.UNDER_REVIEW: {
            MarketSignalStatus.VERIFIED,
            MarketSignalStatus.REJECTED,
            MarketSignalStatus.ARCHIVED,
        },
        MarketSignalStatus.VERIFIED: {MarketSignalStatus.ARCHIVED},
        MarketSignalStatus.REJECTED: set(),
        MarketSignalStatus.ARCHIVED: set(),
    }
    candidate_transitions = {
        RequirementCandidateStatus.CANDIDATE: {
            RequirementCandidateStatus.UNDER_REVIEW,
            RequirementCandidateStatus.REJECTED,
        },
        RequirementCandidateStatus.UNDER_REVIEW: {
            RequirementCandidateStatus.ACCEPTED,
            RequirementCandidateStatus.REJECTED,
        },
        RequirementCandidateStatus.ACCEPTED: set(),
        RequirementCandidateStatus.REJECTED: set(),
        RequirementCandidateStatus.CONVERTED: set(),
    }
    strong_types = {
        MarketSignalType.NEW_WAREHOUSE,
        MarketSignalType.NEW_DISTRIBUTION_CENTER,
        MarketSignalType.LOGISTICS_EXPANSION,
        MarketSignalType.DISTRIBUTION_EXPANSION,
    }
    moderate_types = {
        MarketSignalType.COMPANY_EXPANSION,
        MarketSignalType.ECOMMERCE_EXPANSION,
        MarketSignalType.MARKET_ENTRY,
        MarketSignalType.CAPACITY_EXPANSION,
    }
    possible_types = {
        MarketSignalType.MANUFACTURING_EXPANSION,
        MarketSignalType.NEW_FACILITY,
        MarketSignalType.INDUSTRIAL_INVESTMENT,
        MarketSignalType.LAND_ACQUISITION,
        MarketSignalType.GOVERNMENT_TENDER,
    }

    def list_signals(self, db: Session, organization_id: int, **filters):
        query = select(MarketSignal).where(MarketSignal.organization_id == organization_id)
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(MarketSignal, field) == value)
        return list(db.scalars(query.order_by(MarketSignal.id.desc())).all())

    def get_signal(self, db: Session, signal_id: int):
        return db.get(MarketSignal, signal_id)

    def create_signal(self, db: Session, data: MarketSignalCreate, user: User):
        self._validate_company(db, data.organization_id, data.company_id)
        values = data.model_dump()
        values["created_by_user_id"] = user.id
        if values.get("detected_at") is None:
            values.pop("detected_at")
        signal = MarketSignal(**values)
        db.add(signal)
        self._commit(db)
        db.refresh(signal)
        return signal

    def update_signal(self, db: Session, signal: MarketSignal, data: MarketSignalUpdate):
        values = data.model_dump(exclude_unset=True)
        if "company_id" in values:
            self._validate_company(db, signal.organization_id, values["company_id"])
        for key, value in values.items():
            setattr(signal, key, value)
        self._commit(db)
        db.refresh(signal)
        return signal

    def transition_signal(self, db: Session, signal: MarketSignal, target_status: MarketSignalStatus, user: User, review_notes: str | None = None):
        self._validate_transition(signal.status, target_status, self.signal_transitions, "market signal")
        signal.status = target_status
        if target_status in {MarketSignalStatus.VERIFIED, MarketSignalStatus.REJECTED}:
            signal.reviewed_by_user_id = user.id
            signal.reviewed_at = datetime.utcnow()
            signal.review_notes = review_notes
        self._commit(db)
        db.refresh(signal)
        return signal

    def list_evidence(self, db: Session, signal_id: int):
        return list(db.scalars(select(MarketSignalEvidence).where(MarketSignalEvidence.market_signal_id == signal_id).order_by(MarketSignalEvidence.id)).all())

    def get_evidence(self, db: Session, signal_id: int, evidence_id: int):
        return db.scalar(select(MarketSignalEvidence).where(MarketSignalEvidence.market_signal_id == signal_id, MarketSignalEvidence.id == evidence_id))

    def create_evidence(self, db: Session, signal_id: int, data: MarketSignalEvidenceCreate):
        values = data.model_dump()
        if values.get("recorded_at") is None:
            values.pop("recorded_at")
        evidence = MarketSignalEvidence(market_signal_id=signal_id, **values)
        db.add(evidence)
        self._commit(db)
        db.refresh(evidence)
        return evidence

    def update_evidence(self, db: Session, evidence: MarketSignalEvidence, data: MarketSignalEvidenceUpdate):
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(evidence, key, value)
        self._commit(db)
        db.refresh(evidence)
        return evidence

    def assess(self, db: Session, signal: MarketSignal) -> MarketSignalAssessmentResponse:
        evidence = self.list_evidence(db, signal.id)
        if signal.status == MarketSignalStatus.REJECTED:
            observed = [item.title for item in evidence]
            recommendation = "Do not create a requirement candidate."
            return MarketSignalAssessmentResponse(
                market_signal_id=signal.id,
                indicates_potential_warehouse_demand=False,
                demand_strength=DemandStrength.NONE,
                confidence_level=signal.confidence_level,
                explanation="Rejected market signals do not drive warehouse-demand recommendations.",
                reasons=["Signal status is REJECTED"],
                recommended_next_step=recommendation,
                observed_evidence=observed,
                inference="The rejected signal is not treated as a warehouse-demand opportunity.",
                recommendation=recommendation,
            )
        if signal.signal_type in self.strong_types:
            strength = DemandStrength.STRONG
            explanation = f"Signal type {signal.signal_type.value} is a strong indicator of logistics infrastructure demand."
        elif signal.signal_type in self.moderate_types:
            strength = DemandStrength.MODERATE
            explanation = f"Signal type {signal.signal_type.value} indicates possible operational growth that may require warehouse capacity."
        elif signal.signal_type in self.possible_types:
            strength = DemandStrength.POSSIBLE
            explanation = f"{signal.signal_type.value} may create logistics demand, but it does not explicitly confirm a warehouse requirement."
        else:
            strength = DemandStrength.WEAK
            explanation = "This signal type is not, by itself, a reliable warehouse-demand indicator."
        if signal.status == MarketSignalStatus.VERIFIED:
            explanation += f" The signal is VERIFIED and supported by {len(evidence)} recorded evidence item(s)."
        elif evidence:
            explanation += f" The signal has {len(evidence)} recorded evidence item(s), but remains {signal.status.value}."
        observed = [item.title for item in evidence]
        recommendation = "Review evidence and company linkage before creating a requirement candidate."
        return MarketSignalAssessmentResponse(
            market_signal_id=signal.id,
            indicates_potential_warehouse_demand=strength != DemandStrength.NONE and signal.status != MarketSignalStatus.ARCHIVED,
            demand_strength=strength,
            confidence_level=signal.confidence_level,
            explanation=explanation,
            reasons=[f"Signal type: {signal.signal_type.value}", f"Signal status: {signal.status.value}", f"Evidence items: {len(evidence)}"],
            recommended_next_step=recommendation,
            observed_evidence=observed,
            inference=explanation,
            recommendation=recommendation,
        )

    def create_candidate(self, db: Session, signal: MarketSignal):
        assessment = self.assess(db, signal)
        if signal.status in {MarketSignalStatus.REJECTED, MarketSignalStatus.ARCHIVED}:
            raise CandidateNotEligible("Signal status does not permit a requirement candidate")
        if signal.company_id is None:
            raise CandidateNotEligible("A company must be linked before creating a requirement candidate")
        evidence = self.list_evidence(db, signal.id)
        if signal.status != MarketSignalStatus.VERIFIED:
            raise CandidateNotEligible("Only VERIFIED signals can create requirement candidates")
        if not evidence and signal.confidence_level != MarketSignalConfidence.HIGH:
            raise CandidateNotEligible("Verified signal requires evidence or HIGH confidence")
        existing = db.scalar(select(RequirementCandidate).where(RequirementCandidate.market_signal_id == signal.id))
        if existing is not None:
            raise CandidateAlreadyExists("Requirement candidate already exists for this signal")
        candidate = RequirementCandidate(
            organization_id=signal.organization_id,
            company_id=signal.company_id,
            market_signal_id=signal.id,
            demand_strength=assessment.demand_strength,
            confidence_level=signal.confidence_level,
            summary=signal.title,
            reasoning=assessment.explanation,
            city=signal.city,
            district=signal.district,
            state=signal.state,
            country=signal.country,
        )
        db.add(candidate)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            if self._is_candidate_uniqueness_error(exc):
                raise CandidateAlreadyExists("Requirement candidate already exists for this signal") from exc
            raise
        db.refresh(candidate)
        return candidate

    def list_candidates(self, db: Session, organization_id: int, **filters):
        query = select(RequirementCandidate).where(RequirementCandidate.organization_id == organization_id)
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(RequirementCandidate, field) == value)
        return list(db.scalars(query.order_by(RequirementCandidate.id.desc())).all())

    def get_candidate(self, db: Session, candidate_id: int):
        return db.get(RequirementCandidate, candidate_id)

    def update_candidate(self, db: Session, candidate: RequirementCandidate, data: RequirementCandidateUpdate, user: User):
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(candidate, key, value)
        self._commit(db)
        db.refresh(candidate)
        return candidate

    def transition_candidate(self, db: Session, candidate: RequirementCandidate, target_status: RequirementCandidateStatus, user: User):
        if target_status == RequirementCandidateStatus.CONVERTED:
            raise InvalidStatusTransition("CONVERTED is reserved for a future requirement conversion workflow")
        self._validate_transition(candidate.status, target_status, self.candidate_transitions, "requirement candidate")
        candidate.status = target_status
        if target_status in {RequirementCandidateStatus.ACCEPTED, RequirementCandidateStatus.REJECTED}:
            candidate.reviewed_by_user_id = user.id
            candidate.reviewed_at = datetime.utcnow()
        self._commit(db)
        db.refresh(candidate)
        return candidate

    @staticmethod
    def _validate_company(db: Session, organization_id: int, company_id: int | None):
        if company_id is not None and db.scalar(select(Company.id).where(Company.id == company_id, Company.organization_id == organization_id)) is None:
            raise InvalidCompanyOrganization("Company does not belong to the organization")

    @staticmethod
    def _validate_transition(current_status, target_status, transitions, entity_name):
        if target_status == current_status:
            raise InvalidStatusTransition(f"{entity_name} is already {current_status.value}")
        if target_status not in transitions[current_status]:
            raise InvalidStatusTransition(
                f"Invalid {entity_name} status transition: {current_status.value} -> {target_status.value}"
            )

    @staticmethod
    def _commit(db: Session):
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _is_candidate_uniqueness_error(exc: IntegrityError) -> bool:
        constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint_name is not None:
            return constraint_name == "uq_requirement_candidates__market_signal"
        return str(exc.orig) == "uq_requirement_candidates__market_signal"