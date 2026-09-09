"""Explainable action policy v1; does not change the established score policy."""
from app.models.lead import Lead, LeadStatus
from app.models.lead_activity import ActivityOutcome
from app.models.warehouse_match import WarehouseMatch
from app.schemas.lead_intelligence import (
    LeadIntelligenceContext, LeadMatchEvidence, LeadNextAction,
)


def explain_next_action(
    lead: Lead, factors: dict[str, bool], *, contact_id: int | None,
    requirement_id: int | None, viable_matches: list[WarehouseMatch],
    latest_outcome: ActivityOutcome | None = None,
) -> LeadIntelligenceContext:
    missing = []
    for factor, description in (
        ("company.associated", "Associated company is missing."),
        ("company.industry", "Company industry is missing."),
        ("decision_maker.exists", "Named, eligible decision maker is missing."),
        ("decision_maker.designation", "Selected contact lacks a designation or recognized decision level."),
        ("requirement.active", "Active warehouse requirement is missing."),
        ("requirement.size", "Selected active requirement lacks valid size information."),
        ("requirement.location", "Selected active requirement lacks city or pincode."),
        ("requirement.budget", "Selected active requirement lacks a positive budget."),
        ("requirement.details", "Selected active requirement lacks warehouse type or goods/storage details."),
    ):
        if not factors.get(factor):
            missing.append(description)
    contactable = factors.get("decision_maker.email", False) or factors.get("decision_maker.phone", False)
    if not contactable:
        missing.append("Selected contact has neither email nor phone recorded.")
    requirement = next((item for item in lead.requirements if item.id == requirement_id), None)
    if requirement is None or requirement.move_in_timeframe is None:
        missing.append("Selected active requirement move-in timeline is missing.")

    # Workflow status takes precedence over completeness: never recommend
    # prospecting a closed/disqualified lead or reopening it automatically.
    if lead.status in {LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED, LeadStatus.DORMANT}:
        action = LeadNextAction.MONITOR
        reason = f"Lead status is {lead.status.value}; no new outreach is recommended."
    elif latest_outcome == ActivityOutcome.NOT_INTERESTED:
        action = LeadNextAction.MONITOR
        reason = "Latest completed meaningful activity records NOT_INTERESTED; review before further outreach, even if an older follow-up plan exists."
    elif not factors.get("company.associated") or not factors.get("company.industry"):
        action = LeadNextAction.RESEARCH_COMPANY
        reason = "Record the associated company and its industry before qualifying outreach."
    elif not factors.get("decision_maker.exists"):
        action = LeadNextAction.FIND_DECISION_MAKER
        reason = "No named, non-disqualified contact belongs to the lead's company."
    elif latest_outcome == ActivityOutcome.BOUNCED:
        action = LeadNextAction.RESEARCH_CONTACT
        reason = "Latest completed meaningful activity records BOUNCED; review contact details before further outreach."
    elif not contactable or not factors.get("decision_maker.designation"):
        action = LeadNextAction.RESEARCH_CONTACT
        reason = f"Selected decision maker {contact_id} needs contact details or a recognized decision role."
    elif not all(factors.get(key) for key in ("requirement.active", "requirement.size", "requirement.location")):
        action = LeadNextAction.REVIEW_REQUIREMENT
        reason = "Record an active requirement with valid size and location before matching stock."
    elif not factors.get("warehouse_match.viable"):
        action = LeadNextAction.FIND_WAREHOUSE_MATCH
        reason = "No eligible saved warehouse match scores at least 50 for available stock; run or review warehouse matching."
    elif factors.get("activity.positive") or factors.get("activity.follow_up"):
        action = LeadNextAction.FOLLOW_UP
        reason = "A positive latest engagement or recorded follow-up plan exists; review the activity before following up. This does not imply it is due now."
    elif factors.get("activity.meaningful"):
        action = LeadNextAction.MONITOR
        reason = "Outreach is recorded without a positive latest outcome or follow-up plan; review the activity before further contact."
    else:
        action = LeadNextAction.CONTACT_DECISION_MAKER
        reason = f"Selected decision maker {contact_id} has recorded contact details and role, an active requirement has size/location, and an eligible saved match exists. Contact details are not verified."

    best = max(viable_matches, key=lambda match: (match.match_score, -match.id), default=None)
    evidence = None if best is None else LeadMatchEvidence(
        match_id=best.id, warehouse_id=best.warehouse_id, requirement_id=best.requirement_id,
        match_score=float(best.match_score), status=best.status.value,
        model_version=best.model_version, requirement_compatibility=best.requirement_compatibility,
        match_reasons=best.match_reasons, concern_reasons=best.concern_reasons,
    )
    return LeadIntelligenceContext(
        recommended_action=action, action_reason=reason,
        research_required=action in {
            LeadNextAction.RESEARCH_COMPANY, LeadNextAction.FIND_DECISION_MAKER,
            LeadNextAction.RESEARCH_CONTACT, LeadNextAction.REVIEW_REQUIREMENT,
        },
        missing_information=missing,
        limitations=[
            "Contact verification is not represented in the decision-maker model; recorded details are not verified.",
            "Saved warehouse scores are reused, not recalculated; technical, compliance and timeline compatibility are not independently established by lead scoring.",
        ],
        selected_decision_maker_id=contact_id, selected_requirement_id=requirement_id,
        best_warehouse_match=evidence,
    )