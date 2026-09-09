from datetime import datetime, timezone
from heapq import heappush, heapreplace

from sqlalchemy.orm import Session

from app.models.decision_maker import DecisionLevel, DecisionMakerStatus
from app.models.lead import Lead, LeadPriority, LeadStatus, MoveInTimeframe
from app.models.lead_activity import ActivityOutcome, ActivityStatus
from app.models.lead_score_snapshot import LeadScoreSnapshot
from app.models.requirement import Requirement, RequirementStatus
from app.models.warehouse import AvailabilityStatus
from app.models.warehouse_match import WarehouseMatchStatus
from app.repositories.lead import LeadRepository
from app.repositories.lead_score_snapshot import LeadScoreSnapshotRepository
from app.schemas.lead_intelligence import (
    LeadIntelligenceResponse, LeadScoringReason, PrioritizedLead, PrioritizedLeadResponse,
)
from app.services.lead_actions import explain_next_action
from app.services.lead_scoring_rules import (
    HIGH_MATCH_SCORE, MEANINGFUL_ACTIVITY_TYPES, SCORING_RULES,
    PRIORITY_THRESHOLDS, SCORING_VERSION, VIABLE_MATCH_SCORE, classify_priority,
)


def _text(value: str | None) -> bool:
    return bool(value and value.strip())


def _positive(value) -> bool:
    return value is not None and value > 0


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _requirement_factors(requirement: Requirement) -> dict[str, bool]:
    areas = (
        requirement.required_builtup_area, requirement.required_open_area,
        requirement.minimum_area, requirement.maximum_area,
    )
    valid_area = (
        any(_positive(area) for area in areas)
        and all(area is None or area >= 0 for area in areas)
        and (requirement.minimum_area is None or requirement.maximum_area is None
             or requirement.minimum_area <= requirement.maximum_area)
    )
    return {
        "requirement.active": True,
        "requirement.size": valid_area,
        "requirement.location": _text(requirement.preferred_city) or _text(requirement.preferred_pincode),
        "requirement.urgency": requirement.move_in_timeframe in {
            MoveInTimeframe.IMMEDIATE, MoveInTimeframe.ONE_TO_THREE_MONTHS,
        },
        "requirement.budget": _positive(requirement.budget_per_sqft),
        "requirement.details": requirement.warehouse_type is not None and (
            _text(requirement.goods_type) or _text(requirement.storage_type)
        ),
    }


def evaluate_lead(lead: Lead, *, calculated_at: datetime) -> LeadIntelligenceResponse:
    """Pure evaluation of an eagerly loaded graph; no writes, clock reads or APIs.

    Use one best contact and one best active requirement, not a synthetic profile
    assembled from incomplete rows. Database IDs break equal-score ties.
    """
    company = lead.company
    factors = {
        "company.associated": company is not None,
        "company.organization": company is not None and company.organization_owners is not None,
        "company.industry": company is not None and _text(company.industry),
        "company.legal_name": company is not None and _text(company.legal_name),
        "company.website": company is not None and _text(company.website),
        "company.location": company is not None and _text(company.headquarters_city) and _text(company.headquarters_state),
        "company.products": company is not None and _text(company.products),
    }
    contacts = [
        contact for contact in (company.decision_makers if company else [])
        if contact.company_id == lead.company_id
        and contact.decision_maker_status != DecisionMakerStatus.DISQUALIFIED
        and _text(contact.full_name)
    ]
    contact_candidates = []
    for contact in contacts:
        values = {
            "decision_maker.exists": True,
            "decision_maker.designation": _text(contact.designation) and contact.decision_level in {
                DecisionLevel.C_SUITE, DecisionLevel.VP, DecisionLevel.DIRECTOR,
                DecisionLevel.MANAGER, DecisionLevel.EXECUTIVE,
            },
            "decision_maker.email": _text(contact.email),
            "decision_maker.phone": _text(contact.phone),
        }
        contact_candidates.append((sum(SCORING_RULES[key].points for key, ok in values.items() if ok), contact.id, values))
    selected_contact_id = None
    if contact_candidates:
        _, selected_contact_id, values = max(contact_candidates, key=lambda item: (item[0], -item[1]))
        factors.update(values)
    factors["decision_maker.multiple"] = sum(
        _text(contact.email) or _text(contact.phone) for contact in contacts
    ) >= 2

    active_requirements = [
        requirement for requirement in lead.requirements
        if requirement.lead_id == lead.id and requirement.requirement_status == RequirementStatus.ACTIVE
    ]
    requirement_candidates = []
    for requirement in active_requirements:
        values = _requirement_factors(requirement)
        requirement_candidates.append((sum(SCORING_RULES[key].points for key, ok in values.items() if ok), requirement.id, values))
    selected_requirement_id = None
    if requirement_candidates:
        _, selected_requirement_id, values = max(requirement_candidates, key=lambda item: (item[0], -item[1]))
        factors.update(values)

    activities = [activity for activity in lead.activities if activity.lead_id == lead.id]
    completed = [activity for activity in activities if activity.status == ActivityStatus.COMPLETED]
    meaningful = [activity for activity in completed if activity.activity_type in MEANINGFUL_ACTIVITY_TYPES]
    latest = max(meaningful, key=lambda activity: (_utc(activity.activity_date), activity.id), default=None)
    factors.update({
        "activity.completed": bool(completed),
        "activity.meaningful": bool(meaningful),
        "activity.positive": latest is not None and latest.outcome in {
            ActivityOutcome.INTERESTED, ActivityOutcome.CALLBACK_SCHEDULED,
        },
        "activity.follow_up": any(
            activity.status != ActivityStatus.CANCELLED
            and activity.next_followup_date is not None
            and _utc(activity.next_followup_date) > _utc(activity.activity_date)
            for activity in activities
        ),
    })
    active_ids = {requirement.id for requirement in active_requirements}
    viable = [
        match for match in lead.warehouse_matches
        if match.lead_id == lead.id
        and match.status in {
            WarehouseMatchStatus.AI_RECOMMENDED, WarehouseMatchStatus.SHORTLISTED,
            WarehouseMatchStatus.PROPOSED, WarehouseMatchStatus.LEAD_CHOSEN,
        }
        and (match.requirement_id is None or match.requirement_id in active_ids)
        and match.warehouse is not None
        and match.warehouse.availability_status in {
            AvailabilityStatus.AVAILABLE, AvailabilityStatus.PARTIALLY_OCCUPIED,
        }
        and match.match_score is not None and VIABLE_MATCH_SCORE <= match.match_score <= 100
    ]
    factors.update({
        "warehouse_match.viable": bool(viable),
        "warehouse_match.high_quality": any(match.match_score >= HIGH_MATCH_SCORE for match in viable),
        "warehouse_match.multiple": len({match.warehouse_id for match in viable}) >= 2,
    })
    reasons = []
    for factor, rule in SCORING_RULES.items():
        awarded = bool(factors.get(factor, False))
        explanation = rule.awarded if awarded else rule.missing
        if factor.startswith("decision_maker.") and factor != "decision_maker.multiple" and selected_contact_id is not None:
            explanation += f" Selected decision maker: {selected_contact_id}."
        if factor.startswith("requirement.") and selected_requirement_id is not None:
            explanation += f" Selected requirement: {selected_requirement_id}."
        reasons.append(LeadScoringReason(
            factor=factor, points=rule.points if awarded else 0,
            max_points=rule.points, reason=explanation,
        ))
    # Preserve the 25-factor contract and its arithmetic. Attach non-scoring
    # evidence once to an existing reason so the JSON snapshot needs no migration.
    reasons[0].context = explain_next_action(
        lead, factors, contact_id=selected_contact_id,
        requirement_id=selected_requirement_id, viable_matches=viable,
        latest_outcome=latest.outcome if latest is not None else None,
    )
    total_score = max(0, min(100, sum(reason.points for reason in reasons)))
    return LeadIntelligenceResponse(
        lead_id=lead.id, total_score=total_score, priority=classify_priority(total_score),
        scoring_version=SCORING_VERSION, reasons=reasons, calculated_at=calculated_at,
    )


class LeadIntelligenceService:
    def __init__(self) -> None:
        self.lead_repository = LeadRepository()
        self.repository = LeadScoreSnapshotRepository()

    def list_prioritized_leads(
        self, db: Session, *, priority: LeadPriority | None = None, minimum_score: int = 0,
        industry: str | None = None, organization_id: int | None = None,
        has_active_requirement: bool | None = None, status: LeadStatus | None = None,
        research_required: bool | None = None, limit: int = 100, offset: int = 0,
    ) -> PrioritizedLeadResponse:
        if not 1 <= limit <= 100 or not 0 <= offset <= 10000 or not 0 <= minimum_score <= 100:
            raise ValueError("limit must be 1-100, offset 0-10000 and minimum_score 0-100")
        if organization_id is not None and organization_id < 1:
            raise ValueError("organization_id must be positive")
        calculated_at = datetime.now(timezone.utc)
        ranks = {band: len(PRIORITY_THRESHOLDS) - index
                 for index, (_, band) in enumerate(PRIORITY_THRESHOLDS)}
        retained = []
        total = 0
        with db.no_autoflush:
            for lead in self.lead_repository.iter_for_intelligence(
                db, industry=industry, organization_id=organization_id,
                has_active_requirement=has_active_requirement, status=status,
            ):
                result = evaluate_lead(lead, calculated_at=calculated_at)
                if result.total_score < minimum_score or (priority is not None and result.priority != priority):
                    continue
                explanation = result.explanation
                if research_required is not None and (explanation is None or explanation.research_required != research_required):
                    continue
                total += 1
                company = lead.company
                item = PrioritizedLead(
                    lead_id=lead.id, lead_number=lead.lead_number, company_id=lead.company_id,
                    company_name=company.company_name if company else None,
                    organization_id=company.organization_id if company else None,
                    industry=company.industry if company else None, status=lead.status,
                    intelligence=result,
                )
                entry = (ranks[result.priority], result.total_score, -lead.id, item)
                if len(retained) < offset + limit:
                    heappush(retained, entry)
                elif entry[:3] > retained[0][:3]:
                    heapreplace(retained, entry)
        ordered = sorted(retained, key=lambda entry: entry[:3], reverse=True)
        return PrioritizedLeadResponse(
            items=[entry[3] for entry in ordered[offset:offset + limit]],
            total=total, limit=limit, offset=offset, calculated_at=calculated_at,
        )

    def calculate_lead_score(self, db: Session, lead_id: int) -> LeadIntelligenceResponse | None:
        with db.no_autoflush:
            lead = self.lead_repository.get_for_intelligence(db, lead_id)
            if lead is None:
                return None
            return evaluate_lead(lead, calculated_at=datetime.now(timezone.utc))

    def create_score_snapshot(self, db: Session, lead_id: int) -> LeadIntelligenceResponse | None:
        # Repository commits follow the existing architecture. Never commit a
        # caller's unrelated pending edits as a side effect of score persistence.
        if db.new or db.dirty or db.deleted:
            raise ValueError("Score persistence requires a session without pending changes")
        result = self.calculate_lead_score(db, lead_id)
        if result is None:
            return None
        snapshot = LeadScoreSnapshot(
            lead_id=result.lead_id, total_score=result.total_score, priority=result.priority,
            scoring_version=result.scoring_version, calculated_at=result.calculated_at,
            reasons=[reason.model_dump(mode="json") for reason in result.reasons],
        )
        return LeadIntelligenceResponse.model_validate(self.repository.create(db, snapshot))

    def list_score_history(
        self, db: Session, lead_id: int, *, limit: int = 100, offset: int = 0,
    ) -> list[LeadIntelligenceResponse] | None:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("limit must be 1-100 and offset must be non-negative")
        with db.no_autoflush:
            if not self.lead_repository.exists(db, lead_id):
                return None
            return [LeadIntelligenceResponse.model_validate(snapshot) for snapshot in
                    self.repository.get_by_lead_id(db, lead_id, limit=limit, offset=offset)]