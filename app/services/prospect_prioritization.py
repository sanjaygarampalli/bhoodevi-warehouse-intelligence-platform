"""Prospect Prioritization Engine — score & rank leads/opportunities by business priority.

All logic is deterministic, transparent, and relies *only* on fields that already
exist in the BWIP database.  No statistical models, no external AI calls.

Scoring factors (weighted, each 0–100):
  Factor                 Weight  Source
  ─────────────────────  ──────  ───────────────────────────────────
  Intelligence Score       25    ``LeadIntelligenceService.evaluate_lead`` (total_score)
  Warehouse Match          20    Highest non-rejected ``WarehouseMatch.match_score``
  Follow-Up Urgency        20    ``FollowUpTask.due_at`` proximity / overdue status
  Requirement Quality      15    Active ``Requirement`` completeness (area + location)
  Time Urgency             10    ``Lead.move_in_timeframe`` (faster is better)
  Deal Stage Progress      10    Stage_entered_at + maximum stage_order in pipeline
  ─────────────────────  ─────  ───────────────────────────────────
  Total                   100

Priority thresholds:
  CRITICAL  75+
  HIGH      50–74
  MEDIUM    25–49
  LOW        0–24

Next-best-action rules evaluated in priority order:
  1. Lead terminal (WON/LOST/DISQUALIFIED) → MONITOR
  2. Overdue follow-up task               → FOLLOW_UP_OVERDUE
  3. Follow-up due today                  → FOLLOW_UP_TODAY
  4. NEW lead, no decision maker          → FIND_DECISION_MAKER
  5. No active requirement                → QUALIFY_REQUIREMENT
  6. No viable warehouse match            → CREATE_WAREHOUSE_MATCH
  7. Open deal in late stage              → ADVANCE_DEAL
  8. High intelligence, no deal           → CONTACT_IMMEDIATELY
  9. Otherwise                            → MONITOR

Changelog
─────────
v1   — Sprint 5: Initial release (6‑factor weighted scoring).
"""

from datetime import datetime, timezone
from decimal import Decimal
from heapq import heappush, heapreplace

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, raiseload, selectinload

from app.models.company import Company
from app.models.deal import Deal
from app.models.deal_pipeline_stage import DealPipelineStage
from app.models.decision_maker import DecisionMakerStatus
from app.models.follow_up_task import FollowUpTask, as_utc
from app.models.lead import Lead, LeadStatus, MoveInTimeframe
from app.models.requirement import Requirement, RequirementStatus
from app.models.warehouse_match import WarehouseMatch, WarehouseMatchStatus
from app.repositories.lead import LeadRepository
from app.repositories.follow_up_task import FollowUpTaskRepository
from app.repositories.warehouse_match import WarehouseMatchRepository
from app.schemas.prospect_prioritization import (
    LeadPriorityListResponse,
    LeadPriorityResult,
    NextBestAction,
    NextBestActionType,
    OpportunityPriorityListResponse,
    OpportunityPriorityResult,
    PriorityDashboardSummary,
    PriorityFactor,
    PriorityLevel,
    PriorityReason,
)
from app.schemas.lead_intelligence import LeadIntelligenceResponse
from app.services.lead_intelligence import LeadIntelligenceService
from app.services.lead_scoring_rules import VIABLE_MATCH_SCORE


# ---------------------------------------------------------------------------
# Version for snapshot provenance
# ---------------------------------------------------------------------------
PRIORITIZATION_VERSION = "v1"


# ---------------------------------------------------------------------------
# Scoring weights (must sum to 100)
# ---------------------------------------------------------------------------
W_INTELLIGENCE = 25
W_WAREHOUSE_MATCH = 20
W_FOLLOW_UP_URGENCY = 20
W_REQUIREMENT_QUALITY = 15
W_TIME_URGENCY = 10
W_DEAL_STAGE = 10
_WEIGHT_SUM = W_INTELLIGENCE + W_WAREHOUSE_MATCH + W_FOLLOW_UP_URGENCY + W_REQUIREMENT_QUALITY + W_TIME_URGENCY + W_DEAL_STAGE
assert _WEIGHT_SUM == 100, f"Weights must sum to 100, got {_WEIGHT_SUM}"


# ---------------------------------------------------------------------------
# Priority thresholds
# ---------------------------------------------------------------------------
def _classify_priority(score: int) -> PriorityLevel:
    if score >= 75:
        return PriorityLevel.CRITICAL
    if score >= 50:
        return PriorityLevel.HIGH
    if score >= 25:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


# ---------------------------------------------------------------------------
# Helper: positive numeric check
# ---------------------------------------------------------------------------
def _positive(value) -> bool:
    return value is not None and value > 0


def _text(value: str | None) -> bool:
    return bool(value and value.strip())


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


# ===========================================================================
# Scoring functions (pure — no DB access, operate on loaded models)
# ===========================================================================


def _score_intelligence(intelligence: LeadIntelligenceResponse | None) -> tuple[int, str]:
    """Score 0–100 from the existing intelligence engine result."""
    if intelligence is None:
        return 0, "Intelligence score unavailable — lead has not been evaluated."
    return intelligence.total_score, f"Lead intelligence score is {intelligence.total_score}/100."


def _score_warehouse_match(matches: list[WarehouseMatch]) -> tuple[int, str]:
    """Highest non-rejected match score, 0–100.  Returns 0 when no matches exist."""
    viable = [m for m in matches if m.status != WarehouseMatchStatus.REJECTED and m.match_score is not None]
    if not viable:
        return 0, "No viable warehouse matches found."
    best = max(viable, key=lambda m: m.match_score)
    score = int(best.match_score)
    return score, f"Best warehouse match scores {score}/100 (match_id={best.id}, status={best.status.value})."


def _score_follow_up_urgency(tasks: list[FollowUpTask], now: datetime) -> tuple[int, str]:
    """Score based on the most urgent open/active follow-up task.

    Rules:
        Overdue task              → 100
        Due within 3 days         → 75
        Due within 7 days         → 50
        Due beyond 7 days         → 25
        No open tasks             → 0
    """
    active = [t for t in tasks if t.status in ("OPEN", "IN_PROGRESS")]
    if not active:
        return 0, "No open follow-up tasks."

    # Find the task with the earliest due date
    earliest = min(active, key=lambda t: t.due_at)
    due = _utc(earliest.due_at)
    now_utc = _utc(now)

    if due < now_utc:
        return 100, f"Follow-up task #{earliest.id} is overdue (due: {due.date().isoformat()})."
    days_until = (due - now_utc).days
    if days_until <= 3:
        return 75, f"Follow-up task #{earliest.id} is due within {days_until} day(s)."
    if days_until <= 7:
        return 50, f"Follow-up task #{earliest.id} is due in {days_until} days."
    return 25, f"Follow-up task #{earliest.id} is due in {days_until} days (no immediate urgency)."


def _score_requirement_quality(requirements: list[Requirement]) -> tuple[int, str]:
    """Score 0–100 for completeness of the best active requirement.

    Awarded points:
        Has active requirement               → base 40
        + specified area (builtup/open)      → +30
        + specified city or pincode          → +30
    Missing all → 0.
    """
    active = [r for r in requirements if r.requirement_status == RequirementStatus.ACTIVE]
    if not active:
        return 0, "No active requirement exists."

    best = max(active, key=lambda r: (
        _positive(r.required_builtup_area) or _positive(r.required_open_area) or _positive(r.minimum_area)
    ))
    score = 40  # Has an active requirement
    reasons_parts = [f"Active requirement #{best.id} exists"]

    has_area = _positive(best.required_builtup_area) or _positive(best.required_open_area) or _positive(best.minimum_area)
    if has_area:
        score += 30
        reasons_parts.append("specifies required area")

    has_location = _text(best.preferred_city) or _text(best.preferred_pincode)
    if has_location:
        score += 30
        reasons_parts.append("specifies location (city/pincode)")

    return score, "Requirement quality: " + "; ".join(reasons_parts) + "."


def _score_time_urgency(lead: Lead) -> tuple[int, str]:
    """Score based on move-in timeframe.  Faster = higher score.

    IMMEDIATE         → 100
    1-3 months        → 75
    3-6 months        → 50
    6-12 months       → 25
    FLEXIBLE / None   → 0
    """
    timeframe = lead.move_in_timeframe
    if timeframe == MoveInTimeframe.IMMEDIATE:
        return 100, "Move-in timeframe: IMMEDIATE."
    if timeframe == MoveInTimeframe.ONE_TO_THREE_MONTHS:
        return 75, "Move-in timeframe: 1–3 months."
    if timeframe == MoveInTimeframe.THREE_TO_SIX_MONTHS:
        return 50, "Move-in timeframe: 3–6 months."
    if timeframe == MoveInTimeframe.SIX_TO_TWELVE_MONTHS:
        return 25, "Move-in timeframe: 6–12 months."
    return 0, "Move-in timeframe is flexible or not specified."


def _score_deal_stage(deal: Deal | None, max_order: int) -> tuple[int, str]:
    """Score 0-100 based on deal stage progression.

    If no deal exists, score 0 (neutral, no factor is better or worse).
    If deal is WON -> 100, LOST -> 0.
    Open deals: (current_stage_order / max_stage_order) * 100.
    """
    if deal is None:
        return 0, "No deal/opportunity exists for this lead."
    if deal.deal_status == "WON":
        return 100, "Deal is WON."
    if deal.deal_status == "LOST":
        return 0, "Deal is LOST."
    if max_order <= 0:
        return 0, "Deal pipeline has no defined stages."
    stage_order = deal.stage.stage_order if deal.stage else 0
    pct = int((stage_order / max_order) * 100)
    return pct, f"Deal is at stage '{deal.stage.stage_name if deal.stage else '?'}' ({stage_order}/{max_order})."


# ===========================================================================
# Next-best-action logic
# ===========================================================================


def _determine_next_action(
    lead: Lead,
    tasks: list[FollowUpTask],
    requirements: list[Requirement],
    matches: list[WarehouseMatch],
    deal: Deal | None,
    intelligence: LeadIntelligenceResponse | None,
    now: datetime,
) -> NextBestAction | None:
    """Determine the next best action per the priority-ordered rules.

    Returns ``None`` only if no rule matches (should not happen due to catch-all).
    """
    now_utc = _utc(now)

    # Helper: find earliest open task
    def _earliest_active(tasks: list[FollowUpTask]) -> FollowUpTask | None:
        active = [t for t in tasks if t.status in ("OPEN", "IN_PROGRESS")]
        return min(active, key=lambda t: t.due_at) if active else None

    # Rule 1: Terminal lead → MONITOR
    if lead.status in (LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED):
        return NextBestAction(
            action=NextBestActionType.MONITOR,
            summary=f"Lead status is {lead.status.value} — no action required.",
            reason=f"Lead #{lead.id} has a terminal status ({lead.status.value}). Keep monitoring for reactivation signals.",
        )

    # Rule 2: Overdue follow-up task → FOLLOW_UP_OVERDUE
    earliest_task = _earliest_active(tasks)
    if earliest_task is not None and _utc(earliest_task.due_at) < now_utc:
        return NextBestAction(
            action=NextBestActionType.FOLLOW_UP_OVERDUE,
            summary=f"Follow-up overdue — task '{earliest_task.subject}' was due {earliest_task.due_at.date().isoformat()}.",
            reason=f"Task #{earliest_task.id} is overdue. Contact the lead urgently to re-engage.",
            reference_id=earliest_task.id,
            reference_type="task",
        )

    # Rule 3: Follow-up due today → FOLLOW_UP_TODAY
    if earliest_task is not None and _utc(earliest_task.due_at).date() == now_utc.date():
        return NextBestAction(
            action=NextBestActionType.FOLLOW_UP_TODAY,
            summary=f"Follow-up scheduled today — '{earliest_task.subject}'.",
            reason=f"Task #{earliest_task.id} is due today. Execute the planned outreach.",
            reference_id=earliest_task.id,
            reference_type="task",
        )

    # Rule 4: NEW lead, no decision maker → FIND_DECISION_MAKER
    if lead.status == LeadStatus.NEW and lead.primary_decision_maker_id is None:
        return NextBestAction(
            action=NextBestActionType.FIND_DECISION_MAKER,
            summary="New lead with no decision maker identified.",
            reason=f"Lead #{lead.id} is NEW but has no primary decision maker. Research the company to find a contact.",
        )

    # Rule 5: No active requirement → QUALIFY_REQUIREMENT
    active_reqs = [r for r in requirements if r.requirement_status == RequirementStatus.ACTIVE]
    if not active_reqs:
        return NextBestAction(
            action=NextBestActionType.QUALIFY_REQUIREMENT,
            summary="Lead has no active requirement.",
            reason=f"Lead #{lead.id} has no active requirement. Qualify the lead to understand their warehouse needs.",
        )

    # Rule 6: No viable warehouse match → CREATE_WAREHOUSE_MATCH
    viable_matches = [m for m in matches if m.status != WarehouseMatchStatus.REJECTED]
    if not viable_matches:
        return NextBestAction(
            action=NextBestActionType.CREATE_WAREHOUSE_MATCH,
            summary="No warehouse matches found for this lead's requirement.",
            reason=f"Lead #{lead.id} has an active requirement but no warehouse matches. Generate matches from available inventory.",
        )

    # Rule 7: Open deal in late stage → ADVANCE_DEAL
    if deal is not None and deal.deal_status == "OPEN" and deal.stage is not None:
        if deal.stage.stage_order >= 2:  # NEGOTIATION or beyond
            return NextBestAction(
                action=NextBestActionType.ADVANCE_DEAL,
                summary=f"Deal '{deal.deal_name}' is at stage '{deal.stage.stage_name}'.",
                reason=f"Deal #{deal.id} is in an advanced pipeline stage ({deal.stage.stage_name}). Push toward closure.",
                reference_id=deal.id,
                reference_type="deal",
            )

    # Rule 8: High intelligence, no deal → CONTACT_IMMEDIATELY
    if intelligence is not None and intelligence.total_score >= 50 and deal is None:
        return NextBestAction(
            action=NextBestActionType.CONTACT_IMMEDIATELY,
            summary="High-scoring lead with no open deal — contact now.",
            reason=f"Lead #{lead.id} scores {intelligence.total_score}/100 on intelligence but has no deal. Prioritize outreach.",
        )

    # Rule 9: Catch-all — MONITOR or REENGAGE based on status
    if lead.status == LeadStatus.DORMANT:
        return NextBestAction(
            action=NextBestActionType.REENGAGE_LEAD,
            summary="Dormant lead — consider re-engagement.",
            reason=f"Lead #{lead.id} is DORMANT. Plan a re-engagement campaign.",
        )
    return NextBestAction(
        action=NextBestActionType.MONITOR,
        summary="No immediate action required.",
        reason=f"Lead #{lead.id} is being monitored. All criteria are satisfied or status is current.",
    )


# ===========================================================================
# Top-level evaluation — Lead
# ===========================================================================


def evaluate_lead_priority(
    lead: Lead,
    tasks: list[FollowUpTask],
    deal: Deal | None,
    intelligence: LeadIntelligenceResponse | None,
    max_stage_order: int,
    *,
    evaluated_at: datetime | None = None,
) -> LeadPriorityResult:
    """Compute the priority score and next best action for a single lead.

    Parameters
    ----------
    lead :
        Lead model with eager-loaded ``requirements``, ``warehouse_matches``,
        and relationships reachable through the standard intelligence load options.
    tasks :
        Follow-up tasks for this lead (filtered externally).
    deal :
        Open/Won/Lost deal associated with this lead, or None.
    intelligence :
        Pre-computed intelligence result (optional; None means unavailable).
    max_stage_order :
        Maximum ``stage_order`` across the organization's pipeline stages.
    evaluated_at :
        Timestamp for the evaluation. Defaults to ``datetime.now(timezone.utc)``.

    Returns
    -------
    LeadPriorityResult
    """
    now = evaluated_at or datetime.now(timezone.utc)

    # ── Score each factor ────────────────────────────────────────────
    intel_score, intel_reason = _score_intelligence(intelligence)
    match_score, match_reason = _score_warehouse_match(lead.warehouse_matches)
    urgency_score, urgency_reason = _score_follow_up_urgency(tasks, now)
    req_score, req_reason = _score_requirement_quality(lead.requirements)
    time_score, time_reason = _score_time_urgency(lead)
    stage_score, stage_reason = _score_deal_stage(deal, max_stage_order)

    # ── Weighted total ───────────────────────────────────────────────
    total = (
        (intel_score * W_INTELLIGENCE)
        + (match_score * W_WAREHOUSE_MATCH)
        + (urgency_score * W_FOLLOW_UP_URGENCY)
        + (req_score * W_REQUIREMENT_QUALITY)
        + (time_score * W_TIME_URGENCY)
        + (stage_score * W_DEAL_STAGE)
    ) // _WEIGHT_SUM

    priority = _classify_priority(total)

    # ── Factors list ─────────────────────────────────────────────────
    factors = [
        PriorityFactor(name="intelligence_score", label="AI Lead Intelligence Score", weight=W_INTELLIGENCE, score=intel_score, reason=intel_reason),
        PriorityFactor(name="warehouse_match_score", label="Best Warehouse Match Score", weight=W_WAREHOUSE_MATCH, score=match_score, reason=match_reason),
        PriorityFactor(name="follow_up_urgency", label="Follow-Up Task Urgency", weight=W_FOLLOW_UP_URGENCY, score=urgency_score, reason=urgency_reason),
        PriorityFactor(name="requirement_quality", label="Active Requirement Quality", weight=W_REQUIREMENT_QUALITY, score=req_score, reason=req_reason),
        PriorityFactor(name="time_urgency", label="Move-In Timeframe Urgency", weight=W_TIME_URGENCY, score=time_score, reason=time_reason),
        PriorityFactor(name="deal_stage_progress", label="Deal Pipeline Stage Progress", weight=W_DEAL_STAGE, score=stage_score, reason=stage_reason),
    ]

    # ── Reasons list (human-readable) ────────────────────────────────
    reasons = []
    for factor in factors:
        if factor.score >= 50:
            reasons.append(PriorityReason(factor=factor.name, detail=factor.reason, impact="POSITIVE"))
        elif factor.score == 0:
            reasons.append(PriorityReason(factor=factor.name, detail=factor.reason, impact="MISSING"))

    # ── Next best action ─────────────────────────────────────────────
    action = _determine_next_action(lead, tasks, lead.requirements, lead.warehouse_matches, deal, intelligence, now)

    # ── Derived boolean flags ────────────────────────────────────────
    has_overdue = any(
        t.status in ("OPEN", "IN_PROGRESS") and _utc(t.due_at) < _utc(now)
        for t in tasks
    )
    has_active_req = any(
        r.requirement_status == RequirementStatus.ACTIVE for r in lead.requirements
    )
    has_viable_match = any(
        m.status != WarehouseMatchStatus.REJECTED for m in lead.warehouse_matches
    )

    # ── Company info ─────────────────────────────────────────────────
    company = lead.company
    org_id = company.organization_id if company else None

    return LeadPriorityResult(
        lead_id=lead.id,
        lead_number=lead.lead_number,
        company_id=lead.company_id,
        company_name=company.company_name if company else None,
        organization_id=org_id,
        industry=company.industry if company else None,
        lead_status=lead.status.value if hasattr(lead.status, "value") else str(lead.status),
        priority_level=priority,
        priority_score=total,
        factors=factors,
        reasons=reasons,
        next_best_action=action,
        intelligence_score=intel_score if intel_score > 0 else None,
        follow_up_overdue=has_overdue,
        has_active_requirement=has_active_req,
        has_viable_warehouse_match=has_viable_match,
        opportunity_id=deal.id if deal else None,
        evaluated_at=now,
    )


# ===========================================================================
# Top-level evaluation — Opportunity (Deal)
# ===========================================================================


def evaluate_opportunity_priority(
    deal: Deal,
    intelligence: LeadIntelligenceResponse | None,
    open_tasks: list[FollowUpTask],
    max_stage_order: int,
    *,
    evaluated_at: datetime | None = None,
) -> OpportunityPriorityResult:
    """Compute the priority score and next best action for a single deal.

    Uses a subset of the same scoring factors (intelligence, follow-up urgency,
    deal stage progress) plus deal-specific signals (expected revenue).

    Parameters
    ----------
    deal :
        Deal model with eager-loaded ``stage``, ``lead``, and ``organization``.
    intelligence :
        Pre-computed intelligence result for the underlying lead.
    open_tasks :
        Open/active follow-up tasks linked to this deal or its lead.
    max_stage_order :
        Maximum ``stage_order`` across the organization's pipeline stages.
    evaluated_at :
        Timestamp for the evaluation.

    Returns
    -------
    OpportunityPriorityResult
    """
    now = evaluated_at or datetime.now(timezone.utc)

    lead = deal.lead

    # ── Reuse sub-scores from the lead evaluation ────────────────────
    intel_score, _ = _score_intelligence(intelligence)
    urgency_score, urgency_reason = _score_follow_up_urgency(open_tasks, now)
    stage_score, stage_reason = _score_deal_stage(deal, max_stage_order)

    # Opportunity-specific: expected revenue
    revenue = deal.expected_revenue or Decimal('0')
    if revenue > 0:
        rev_val = float(revenue)
        rev_score = min(100, int(rev_val / 10000000 * 100))
        rev_reason = f'Expected revenue: {revenue:.2f} {deal.currency}.'
    else:
        rev_score = 0
        rev_reason = 'Expected revenue not specified.'

    # Days in stage
    now_utc = _utc(now)
    stage_entered = _utc(deal.stage_entered_at)
    days_in_stage = (now_utc - stage_entered).days if stage_entered else 0

    # Overdue task count
    overdue_count = sum(
        1 for t in open_tasks
        if t.status in ('OPEN', 'IN_PROGRESS') and _utc(t.due_at) < now_utc
    )

    # Weighted total (custom weights for opportunities)
    O_INTEL = 25
    O_URGENCY = 20
    O_STAGE = 25
    O_REVENUE = 30
    O_WEIGHT_SUM = O_INTEL + O_URGENCY + O_STAGE + O_REVENUE

    total = (
        (intel_score * O_INTEL)
        + (urgency_score * O_URGENCY)
        + (stage_score * O_STAGE)
        + (rev_score * O_REVENUE)
    ) // O_WEIGHT_SUM

    priority = _classify_priority(total)

    factors = [
        PriorityFactor(name='intelligence_score', label='AI Lead Intelligence Score', weight=O_INTEL, score=intel_score, reason='See lead-level intelligence.'),
        PriorityFactor(name='follow_up_urgency', label='Follow-Up Task Urgency', weight=O_URGENCY, score=urgency_score, reason=urgency_reason),
        PriorityFactor(name='deal_stage_progress', label='Deal Pipeline Stage Progress', weight=O_STAGE, score=stage_score, reason=stage_reason),
        PriorityFactor(name='expected_revenue', label='Expected Revenue Value', weight=O_REVENUE, score=rev_score, reason=rev_reason),
    ]

    reasons = []
    for factor in factors:
        if factor.score >= 50:
            reasons.append(PriorityReason(factor=factor.name, detail=factor.reason, impact='POSITIVE'))
        elif factor.score == 0:
            reasons.append(PriorityReason(factor=factor.name, detail=factor.reason, impact='MISSING'))

    # Next best action
    if deal.deal_status == 'WON':
        action = NextBestAction(action=NextBestActionType.MONITOR, summary='Deal won. No action required.', reason=f'Deal #{deal.id} is WON.')
    elif deal.deal_status == 'LOST':
        action = NextBestAction(action=NextBestActionType.MONITOR, summary='Deal lost. No action required.', reason=f'Deal #{deal.id} is LOST.')
    elif overdue_count > 0:
        action = NextBestAction(action=NextBestActionType.FOLLOW_UP_OVERDUE, summary=f'{overdue_count} overdue task(s).',
                                reason=f'Deal #{deal.id} has {overdue_count} overdue follow-up task(s).',
                                reference_id=deal.id, reference_type='deal')
    elif deal.stage and deal.stage.stage_order >= 2:
        action = NextBestAction(action=NextBestActionType.ADVANCE_DEAL, summary=f'Advance deal \'{deal.deal_name}\' at \'{deal.stage.stage_name}\'.',
                                reason=f'Deal is in advanced stage ({deal.stage.stage_name}). Work toward closure.',
                                reference_id=deal.id, reference_type='deal')
    else:
        action = NextBestAction(action=NextBestActionType.MONITOR, summary='Monitor deal progression.',
                                reason=f"Deal #{deal.id} is being monitored at stage '{deal.stage.stage_name if deal.stage else '?'}'.")

    return OpportunityPriorityResult(
        deal_id=deal.id,
        deal_name=deal.deal_name,
        organization_id=deal.organization_id,
        organization_name=deal.organization.legal_name if deal.organization else None,
        lead_id=deal.lead_id,
        lead_number=lead.lead_number if lead else None,
        stage_name=deal.stage.stage_name if deal.stage else '?',
        deal_status=deal.deal_status,
        expected_revenue=revenue if revenue > 0 else None,
        priority_level=priority,
        priority_score=total,
        factors=factors,
        reasons=reasons,
        next_best_action=action,
        intelligence_score=intel_score if intel_score > 0 else None,
        overdue_task_count=overdue_count,
        days_in_stage=days_in_stage,
        evaluated_at=now,
    )
class ProspectPrioritizationService:
    def __init__(self):
        self._intelligence_service = LeadIntelligenceService()

    def evaluate_lead(self, db, lead_id, evaluated_at=None):
        i = self._intelligence_service.calculate_lead_score(db, lead_id)
        return self.evaluate_lead_from_db(db, lead_id, i, evaluated_at=evaluated_at)

    def evaluate_lead_from_db(self, db, lead_id, intelligence, evaluated_at=None):
        now = evaluated_at or datetime.now(timezone.utc)
        lead = db.scalar(select(Lead).where(Lead.id == lead_id).options(joinedload(Lead.company)))
        if lead is None:
            return None
        return evaluate_lead_priority(
            lead, tasks_for_lead(db, lead_id), deal_for_lead(db, lead_id),
            intelligence, max_stage_order(db, lead), evaluated_at=now,
        )

    def list_lead_priorities(self, db, limit=50, offset=0, industry=None, organization_id=None,
                              has_active_requirement=None, status=None, minimum_priority_score=0, evaluated_at=None):
        now = evaluated_at or datetime.now(timezone.utc)
        ls = LeadStatus(status) if status and status in {s.value for s in LeadStatus} else None
        total, retained = 0, []
        from app.services.lead_intelligence import evaluate_lead as _eval
        for lead in LeadRepository().iter_for_intelligence(db, industry=industry, organization_id=organization_id, has_active_requirement=has_active_requirement, status=ls):
            i = _eval(lead, calculated_at=now)
            r = evaluate_lead_priority(lead, tasks_for_lead(db, lead.id), deal_for_lead(db, lead.id), i, max_stage_order(db, lead), evaluated_at=now)
            if r.priority_score < minimum_priority_score:
                continue
            total += 1
            e = (list(PriorityLevel).index(r.priority_level), r.priority_score, -lead.id, r)
            entries = retained  # rename
            if len(entries) < offset + limit:
                heappush(entries, e)
            elif e[:3] > entries[0][:3]:
                heapreplace(entries, e)
        ordered = sorted(retained, key=lambda x: x[:3], reverse=True)
        return LeadPriorityListResponse(items=[x[3] for x in ordered[offset:offset+limit]], total=total, limit=limit, offset=offset, evaluated_at=now)

    def evaluate_opportunity(self, db, deal_id, evaluated_at=None):
        now = evaluated_at or datetime.now(timezone.utc)
        deal = db.scalar(select(Deal).where(Deal.id == deal_id).options(joinedload(Deal.stage), joinedload(Deal.organization), joinedload(Deal.lead)))
        if deal is None:
            return None
        i = self._intelligence_service.calculate_lead_score(db, deal.lead_id)
        return evaluate_opportunity_priority(deal, i, tasks_for_lead(db, deal.lead_id), max_stage_order(db, deal.lead), evaluated_at=now)

    def list_opportunity_priorities(self, db, limit=50, offset=0, organization_id=None, minimum_priority_score=0, evaluated_at=None):
        now = evaluated_at or datetime.now(timezone.utc)
        stmt = select(Deal).options(joinedload(Deal.stage), joinedload(Deal.organization), joinedload(Deal.lead)).order_by(Deal.id)
        if organization_id is not None:
            stmt = stmt.where(Deal.organization_id == organization_id)
        total, retained = 0, []
        for deal in db.scalars(stmt).all():
            i = self._intelligence_service.calculate_lead_score(db, deal.lead_id)
            r = evaluate_opportunity_priority(deal, i, tasks_for_lead(db, deal.lead_id), max_stage_order(db, deal.lead), evaluated_at=now)
            if r.priority_score < minimum_priority_score:
                continue
            total += 1
            e = (list(PriorityLevel).index(r.priority_level), r.priority_score, -deal.id, r)
            if len(retained) < offset + limit:
                heappush(retained, e)
            elif e[:3] > retained[0][:3]:
                heapreplace(retained, e)
        ordered = sorted(retained, key=lambda x: x[:3], reverse=True)
        return OpportunityPriorityListResponse(items=[x[3] for x in ordered[offset:offset+limit]], total=total, limit=limit, offset=offset, evaluated_at=now)

    def dashboard_summary(self, db, organization_id=None, top_n=5, evaluated_at=None):
        now = evaluated_at or datetime.now(timezone.utc)
        from app.services.lead_intelligence import evaluate_lead as _eval
        all_leads = list(LeadRepository().iter_for_intelligence(db, organization_id=organization_id))
        lr = []
        for L in all_leads:
            lr.append(evaluate_lead_priority(L, tasks_for_lead(db, L.id), deal_for_lead(db, L.id), _eval(L, calculated_at=now), max_stage_order(db, L), evaluated_at=now))
        cr = sum(1 for r in lr if r.priority_level == PriorityLevel.CRITICAL)
        hi = sum(1 for r in lr if r.priority_level == PriorityLevel.HIGH)
        md = sum(1 for r in lr if r.priority_level == PriorityLevel.MEDIUM)
        lo = sum(1 for r in lr if r.priority_level == PriorityLevel.LOW)
        ov = sum(1 for r in lr if r.follow_up_overdue)
        nc = sum(1 for r in lr if r.next_best_action and r.next_best_action.action in (NextBestActionType.CONTACT_IMMEDIATELY, NextBestActionType.FOLLOW_UP_TODAY, NextBestActionType.FOLLOW_UP_OVERDUE))
        lr.sort(key=lambda r: (-list(PriorityLevel).index(r.priority_level), -r.priority_score))
        stmt = select(Deal).options(joinedload(Deal.stage), joinedload(Deal.organization), joinedload(Deal.lead))
        if organization_id is not None:
            stmt = stmt.where(Deal.organization_id == organization_id)
        opp = [evaluate_opportunity_priority(D, self._intelligence_service.calculate_lead_score(db, D.lead_id), tasks_for_lead(db, D.lead_id), max_stage_order(db, D.lead), evaluated_at=now) for D in db.scalars(stmt).all()]
        opp.sort(key=lambda r: (-list(PriorityLevel).index(r.priority_level), -r.priority_score))
        ra = sum(1 for r in opp if r.next_best_action and r.next_best_action.action == NextBestActionType.ADVANCE_DEAL)
        return PriorityDashboardSummary(total_leads=len(lr), critical_leads=cr, high_priority_leads=hi, medium_priority_leads=md, low_priority_leads=lo, overdue_follow_ups=ov, leads_requiring_contact=nc, opportunities_ready_to_advance=ra, top_lead_priorities=lr[:top_n], top_opportunity_priorities=opp[:top_n], evaluated_at=now)

def tasks_for_lead(db, lead_id):
    return list(db.scalars(select(FollowUpTask).where(FollowUpTask.lead_id == lead_id)).all())

def deal_for_lead(db, lead_id):
    return db.scalar(select(Deal).where(Deal.lead_id == lead_id).options(joinedload(Deal.stage)).order_by(Deal.id.desc()).limit(1))

def max_stage_order(db, lead):
    c = lead.company
    if c is None or c.organization_id is None:
        return 0
    r = db.scalar(select(DealPipelineStage.stage_order).where(DealPipelineStage.organization_id == c.organization_id).order_by(DealPipelineStage.stage_order.desc()).limit(1))
    return r if r is not None else 0
