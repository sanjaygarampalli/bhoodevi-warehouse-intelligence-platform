"""Deterministic, read-only prioritization of companies for human investigation."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_intelligence import CompanyIntelligenceProfile, CompanyWarehouseProfile
from app.models.deal import Deal
from app.models.lead import Lead, LeadStatus
from app.models.market_signal import (
    DemandStrength,
    EvidenceCredibility,
    MarketSignal,
    MarketSignalEvidence,
    MarketSignalStatus,
    MarketSignalType,
)
from app.models.requirement import Requirement, RequirementStatus
from app.schemas.company_prospect_priority import (
    CommercialContext,
    CompanyProspectPriority,
    CompanyProspectPriorityList,
    ScoreReason,
)
from app.schemas.prospect_prioritization import PriorityLevel


class CompanyProspectPriorityService:
    strong_types = {
        MarketSignalType.NEW_WAREHOUSE, MarketSignalType.NEW_DISTRIBUTION_CENTER,
        MarketSignalType.LOGISTICS_EXPANSION, MarketSignalType.DISTRIBUTION_EXPANSION,
    }
    moderate_types = {
        MarketSignalType.COMPANY_EXPANSION, MarketSignalType.ECOMMERCE_EXPANSION,
        MarketSignalType.MARKET_ENTRY, MarketSignalType.CAPACITY_EXPANSION,
    }
    possible_types = {
        MarketSignalType.MANUFACTURING_EXPANSION, MarketSignalType.NEW_FACILITY,
        MarketSignalType.INDUSTRIAL_INVESTMENT, MarketSignalType.LAND_ACQUISITION,
        MarketSignalType.GOVERNMENT_TENDER,
    }

    def assess(self, db: Session, company_id: int) -> CompanyProspectPriority | None:
        company = db.get(Company, company_id)
        if company is None:
            return None
        return self._assess(db, company)

    def list(self, db: Session, organization_id: int) -> CompanyProspectPriorityList:
        companies = list(db.scalars(select(Company).where(Company.organization_id == organization_id).order_by(Company.id)).all())
        items = [self._assess(db, company) for company in companies]
        items.sort(key=lambda item: (-item.priority_score, item.company_name.lower(), item.company_id))
        now = datetime.now(timezone.utc)
        return CompanyProspectPriorityList(items=items, total=len(items), evaluated_at=now)

    def _assess(self, db: Session, company: Company) -> CompanyProspectPriority:
        signals = list(db.scalars(select(MarketSignal).where(
            MarketSignal.organization_id == company.organization_id,
            MarketSignal.company_id == company.id,
        ).order_by(MarketSignal.id)).all())
        verified = [s for s in signals if s.status == MarketSignalStatus.VERIFIED]
        current = [s for s in signals if s.status not in {MarketSignalStatus.REJECTED, MarketSignalStatus.ARCHIVED}]
        evidence = list(db.scalars(select(MarketSignalEvidence).join(
            MarketSignal, MarketSignal.id == MarketSignalEvidence.market_signal_id
        ).where(
            MarketSignal.organization_id == company.organization_id,
            MarketSignal.company_id == company.id,
        ).order_by(MarketSignalEvidence.id)).all())
        verified_evidence = [e for e in evidence if any(e.market_signal_id == s.id for s in verified)]

        reasons: list[ScoreReason] = []
        observed: list[str] = []
        indicators: list[str] = []
        uncertainties: list[str] = []
        demand_rank = {DemandStrength.NONE: 0, DemandStrength.WEAK: 1, DemandStrength.POSSIBLE: 2, DemandStrength.MODERATE: 3, DemandStrength.STRONG: 4}
        strength = DemandStrength.NONE
        for signal in verified:
            candidate = DemandStrength.STRONG if signal.signal_type in self.strong_types else DemandStrength.MODERATE if signal.signal_type in self.moderate_types else DemandStrength.POSSIBLE if signal.signal_type in self.possible_types else DemandStrength.WEAK
            if demand_rank[candidate] > demand_rank[strength]:
                strength = candidate
            observed.append(f"Verified {signal.signal_type.value.replace('_', ' ').lower()} signal: {signal.title}")
            indicators.append(signal.signal_type.value)
        if verified:
            points = {DemandStrength.STRONG: 35, DemandStrength.MODERATE: 25, DemandStrength.POSSIBLE: 15, DemandStrength.WEAK: 5, DemandStrength.NONE: 0}[strength]
            reasons.append(ScoreReason(points=points, reason=f"Highest verified demand signal strength is {strength.value}."))
        elif current:
            uncertainties.append("Recorded signals are not yet verified.")
        else:
            uncertainties.append("No current verified market signal is recorded.")

        credibility_points = {EvidenceCredibility.PRIMARY: 20, EvidenceCredibility.HIGH: 15, EvidenceCredibility.MEDIUM: 8, EvidenceCredibility.LOW: 3}
        evidence_points = min(25, max((credibility_points[e.credibility_level] for e in verified_evidence), default=0) + max(0, min(5, len(verified_evidence) - 1) * 2))
        if verified_evidence:
            observed.append(f"{len(verified_evidence)} evidence record(s) support verified signals.")
            reasons.append(ScoreReason(points=evidence_points, reason="Credibility of evidence supporting verified signals."))
        else:
            uncertainties.append("No credible evidence is attached to a verified signal.")

        profile = db.scalar(select(CompanyIntelligenceProfile).where(CompanyIntelligenceProfile.organization_id == company.organization_id, CompanyIntelligenceProfile.company_id == company.id))
        warehouse = db.scalar(select(CompanyWarehouseProfile).where(CompanyWarehouseProfile.organization_id == company.organization_id, CompanyWarehouseProfile.company_id == company.id))
        completeness_fields = [company.industry, company.company_type, company.website, company.headquarters_city, company.headquarters_state, company.products]
        completeness_points = min(10, sum(value is not None and value != "" for value in completeness_fields) * 2)
        if profile:
            completeness_points = min(10, completeness_points + 2)
        if warehouse and getattr(warehouse, "warehouse_dependency", None) and warehouse.warehouse_dependency.value != "UNKNOWN":
            completeness_points = min(10, completeness_points + 2)
            indicators.append(f"Recorded warehouse dependency: {warehouse.warehouse_dependency.value}")
        reasons.append(ScoreReason(points=completeness_points, reason="Company intelligence completeness and recorded warehouse context."))
        if not profile and not warehouse:
            uncertainties.append("Warehouse profile and operational intelligence are incomplete.")

        leads = list(db.scalars(select(Lead).where(Lead.company_id == company.id)).all())
        active_leads = [lead for lead in leads if lead.status not in {LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED}]
        requirements = list(db.scalars(select(Requirement).join(Lead, Requirement.lead_id == Lead.id).where(Lead.company_id == company.id, Requirement.requirement_status.in_([RequirementStatus.DRAFT, RequirementStatus.ACTIVE, RequirementStatus.ON_HOLD]))).all())
        deals = list(db.scalars(select(Deal).join(Lead, Deal.lead_id == Lead.id).where(Deal.organization_id == company.organization_id, Lead.company_id == company.id, Deal.deal_status == "OPEN")).all())
        context = CommercialContext(existing_lead=bool(active_leads), existing_requirement=bool(requirements), active_deal=bool(deals), pipeline_status="ACTIVE OPPORTUNITY" if deals else "QUALIFICATION IN PROGRESS" if requirements or active_leads else "NEW PROSPECT")
        if deals:
            uncertainties.append("Commercial qualification is already active; prospect priority should not create duplicate outreach.")
        if not requirements:
            uncertainties.append("A confirmed warehouse size and operational requirement is not recorded.")

        score = min(100, sum(reason.points for reason in reasons))
        priority = PriorityLevel.CRITICAL if score >= 75 else PriorityLevel.HIGH if score >= 50 else PriorityLevel.MEDIUM if score >= 25 else PriorityLevel.LOW
        if deals:
            action = "Continue the active commercial pipeline; do not create a duplicate prospect workflow."
        elif verified and verified_evidence:
            action = "Investigate the recorded expansion and identify the relevant logistics decision-maker."
        elif current:
            action = "Review and verify the recorded signals before prioritizing outreach."
        else:
            action = "Collect additional company and demand evidence; monitor for new signals."
        confidence = "HIGH" if any(e.credibility_level in {EvidenceCredibility.PRIMARY, EvidenceCredibility.HIGH} for e in verified_evidence) else "MEDIUM" if verified_evidence else "LOW"
        inference = "Recorded expansion may increase logistics or storage needs; this is a human-investigation recommendation, not a confirmed requirement."
        return CompanyProspectPriority(company_id=company.id, organization_id=company.organization_id, company_name=company.company_name, priority=priority, priority_score=score, demand_strength=strength.value, evidence_confidence=confidence, observed_facts=observed, demand_indicators=indicators, commercial_context=context, inference=inference, uncertainties=uncertainties, recommended_next_action=action, human_review_required=True, score_reasons=reasons, evaluated_at=datetime.now(timezone.utc))