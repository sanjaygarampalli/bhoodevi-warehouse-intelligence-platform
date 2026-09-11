"""Orchestrate existing BWIP intelligence into one practical action queue."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.deal import Deal
from app.models.company import Company
from app.models.follow_up_task import FollowUpTask, TaskStatus, as_utc
from app.models.lead import Lead, LeadStatus
from app.models.requirement import Requirement, RequirementStatus
from app.models.warehouse_match import WarehouseMatch, WarehouseMatchStatus
from app.schemas.action_intelligence import (
    ActionIntelligenceSummaryResponse,
    ActionRecommendationListResponse,
    ActionRecommendationResponse,
    ActionType,
)
from app.schemas.prospect_prioritization import PriorityLevel
from app.services.lead_scoring_rules import HIGH_MATCH_SCORE
from app.services.prospect_prioritization import ProspectPrioritizationService

STALE_LEAD_DAYS = 30
ACTIVE_STATUSES = tuple(status for status in LeadStatus if status not in {
    LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED, LeadStatus.DORMANT,
})
OPEN_TASK_STATUSES = (TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value)
ACTION_PRECEDENCE = {
    ActionType.FOLLOW_UP_OVERDUE: 100,
    ActionType.DEAL_AT_RISK: 90,
    ActionType.REVIEW_HIGH_MATCH: 80,
    ActionType.CONTACT_DECISION_MAKER: 70,
    ActionType.FOLLOW_UP: 60,
    ActionType.REENGAGE_COLD_LEAD: 50,
    ActionType.CONTACT_LEAD: 40,
    ActionType.REVIEW_REQUIREMENT: 30,
    ActionType.SCHEDULE_DISCUSSION: 20,
    ActionType.ADVANCE_DEAL: 10,
}


class ActionIntelligenceService:
    """Read-only action orchestration; scoring remains canonical elsewhere."""

    def __init__(self, *, prioritization_service=None, clock=None):
        self.prioritization = prioritization_service or ProspectPrioritizationService()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _priority_for(score: int) -> PriorityLevel:
        if score >= 75:
            return PriorityLevel.CRITICAL
        if score >= 50:
            return PriorityLevel.HIGH
        if score >= 25:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW

    @staticmethod
    def _lead_label(lead):
        return lead.company.company_name if lead.company else lead.lead_number

    def _base(self, action_type, priority, title, reason, *, lead=None, deal=None,
              task=None, match=None, requirement=None, ranking_score=0, source_at=None):
        company = lead.company if lead is not None else None
        contact = lead.primary_decision_maker if lead is not None else None
        return ActionRecommendationResponse(
            id=f"{action_type.value.lower()}:{deal.id if deal else lead.id if lead else task.id}",
            action_type=action_type, priority=priority, title=title, reason=reason,
            recommended_action=title, lead_id=lead.id if lead else None,
            lead_name=lead.lead_number if lead else None,
            company_id=company.id if company else None,
            company_name=company.company_name if company else None,
            decision_maker_id=contact.id if contact else None,
            decision_maker_name=contact.full_name if contact else None,
            deal_id=deal.id if deal else None,
            follow_up_task_id=task.id if task else None,
            warehouse_match_id=match.id if match else None,
            requirement_id=requirement.id if requirement else None,
            due_at=as_utc(task.due_at) if task else None,
            source_at=source_at,
            ranking_score=ranking_score,
        )

    def _build(self, db: Session, now: datetime, organization_id=None):
        lead_results = self.prioritization.list_lead_priorities(
            db, limit=200, organization_id=organization_id, evaluated_at=now,
        ).items
        lead_stmt = select(Lead).join(Company, Lead.company_id == Company.id).options(
            joinedload(Lead.company), joinedload(Lead.primary_decision_maker),
        )
        if organization_id is not None:
            lead_stmt = lead_stmt.where(Company.organization_id == organization_id)
        leads = {lead.id: lead for lead in db.scalars(lead_stmt).all()}
        tasks = list(db.scalars(select(FollowUpTask).where(
            FollowUpTask.status.in_(OPEN_TASK_STATUSES),
        ).where(FollowUpTask.lead_id.in_(leads) if leads else False).order_by(FollowUpTask.due_at, FollowUpTask.id)).all())
        tasks_by_lead = {}
        for task in tasks:
            tasks_by_lead.setdefault(task.lead_id, []).append(task)
        deals = list(db.scalars(select(Deal).options(
            joinedload(Deal.lead).joinedload(Lead.company), joinedload(Deal.stage),
        ).where(Deal.deal_status == "OPEN", Deal.lead_id.in_(leads) if leads else False)).all())
        deals_by_lead = {}
        for deal in deals:
            deals_by_lead.setdefault(deal.lead_id, []).append(deal)
        matches = list(db.scalars(select(WarehouseMatch).where(
            WarehouseMatch.match_score >= HIGH_MATCH_SCORE,
            WarehouseMatch.status.notin_((WarehouseMatchStatus.REJECTED, WarehouseMatchStatus.STALE)),
        ).where(WarehouseMatch.lead_id.in_(leads) if leads else False).order_by(WarehouseMatch.match_score.desc(), WarehouseMatch.id)).all())
        matches_by_lead = {}
        for match in matches:
            matches_by_lead.setdefault(match.lead_id, []).append(match)

        candidates = {}
        for result in lead_results:
            lead = leads.get(result.lead_id)
            if lead is None or lead.status not in ACTIVE_STATUSES:
                continue
            lead_tasks = tasks_by_lead.get(lead.id, [])
            overdue = next((task for task in lead_tasks if as_utc(task.due_at) < now), None)
            if overdue:
                candidate = self._base(ActionType.FOLLOW_UP_OVERDUE, PriorityLevel.CRITICAL,
                    f"Complete overdue follow-up: {overdue.subject}",
                    "An open follow-up task is past its due date.", lead=lead, task=overdue,
                    ranking_score=100 + result.priority_score)
            else:
                risky = next((deal for deal in deals_by_lead.get(lead.id, [])
                              if deal.expected_close_date and deal.expected_close_date < now.date()), None)
                if risky:
                    candidate = self._base(ActionType.DEAL_AT_RISK, PriorityLevel.CRITICAL,
                        f"Intervene on deal: {risky.deal_name}",
                        "This open deal is past its expected close date.", lead=lead, deal=risky,
                        ranking_score=90 + result.priority_score)
                elif matches_by_lead.get(lead.id):
                    match = matches_by_lead[lead.id][0]
                    candidate = self._base(ActionType.REVIEW_HIGH_MATCH, PriorityLevel.HIGH,
                        f"Review warehouse match for {self._lead_label(lead)}",
                        f"Saved warehouse match score is {match.match_score}, above the high-match policy threshold.",
                        lead=lead, match=match, ranking_score=80 + result.priority_score)
                elif lead.primary_decision_maker and not lead.primary_decision_maker.last_contacted_at:
                    candidate = self._base(ActionType.CONTACT_DECISION_MAKER, PriorityLevel.HIGH,
                        f"Contact decision maker at {self._lead_label(lead)}",
                        "A primary decision maker is identified but has no recorded contact date.",
                        lead=lead, ranking_score=70 + result.priority_score)
                elif lead_tasks:
                    task = lead_tasks[0]
                    candidate = self._base(ActionType.FOLLOW_UP, result.priority_level,
                        f"Complete follow-up: {task.subject}",
                        "An open follow-up is scheduled for this prospect.", lead=lead, task=task,
                        ranking_score=60 + result.priority_score)
                else:
                    last_activity = lead.last_activity_at
                    stale = last_activity is None or as_utc(last_activity) < now - timedelta(days=STALE_LEAD_DAYS)
                    if stale:
                        candidate = self._base(ActionType.REENGAGE_COLD_LEAD, result.priority_level,
                            f"Re-engage {self._lead_label(lead)}",
                            f"No recent activity was recorded in the last {STALE_LEAD_DAYS} days.", lead=lead,
                            ranking_score=50 + result.priority_score, source_at=last_activity)
                    elif result.next_best_action and result.next_best_action.action.value == "QUALIFY_REQUIREMENT":
                        candidate = self._base(ActionType.REVIEW_REQUIREMENT, result.priority_level,
                            f"Review requirement for {self._lead_label(lead)}",
                            "The existing prioritization engine identifies requirement qualification as the next step.",
                            lead=lead, ranking_score=30 + result.priority_score)
                    else:
                        candidate = self._base(ActionType.CONTACT_LEAD, result.priority_level,
                            f"Contact {self._lead_label(lead)}",
                            "The existing prioritization engine identifies this active prospect as actionable.",
                            lead=lead, ranking_score=40 + result.priority_score)
            candidates[lead.id] = candidate

        # A deal action may replace a weaker lead action for the same lead.
        for deal in deals:
            if deal.lead_id in candidates:
                continue
            if deal.expected_close_date and deal.expected_close_date < now.date():
                candidates[deal.lead_id] = self._base(ActionType.DEAL_AT_RISK, PriorityLevel.CRITICAL,
                    f"Intervene on deal: {deal.deal_name}",
                    "This open deal is past its expected close date.", lead=deal.lead, deal=deal,
                    ranking_score=100)
        return sorted(candidates.values(), key=lambda item: (
            -list(PriorityLevel).index(item.priority), -item.ranking_score, item.id,
        )), len([x for x in candidates.values() if x.action_type == ActionType.FOLLOW_UP_OVERDUE]), len([x for x in candidates.values() if x.action_type == ActionType.REENGAGE_COLD_LEAD]), len([x for x in candidates.values() if x.action_type == ActionType.DEAL_AT_RISK]), len([x for x in candidates.values() if x.action_type == ActionType.REVIEW_HIGH_MATCH])

    def get_prioritized_actions(self, db, *, limit=50, priority=None, action_type=None, organization_id=None):
        now = self.clock().astimezone(timezone.utc)
        items, *_ = self._build(db, now, organization_id)
        if priority:
            items = [item for item in items if item.priority == priority]
        if action_type:
            items = [item for item in items if item.action_type == action_type]
        return ActionRecommendationListResponse(items=items[:limit], total=len(items), limit=limit, evaluated_at=now)

    def get_today_actions(self, db, *, limit=20, organization_id=None):
        return self.get_prioritized_actions(db, limit=limit, organization_id=organization_id)

    def get_lead_actions(self, db, lead_id, *, limit=50, organization_id=None):
        result = self.get_prioritized_actions(db, limit=100, organization_id=organization_id)
        items = [item for item in result.items if item.lead_id == lead_id]
        return ActionRecommendationListResponse(items=items[:limit], total=len(items), limit=limit, evaluated_at=result.evaluated_at)

    def get_action_summary(self, db, organization_id=None):
        now = self.clock().astimezone(timezone.utc)
        items, overdue, stale, risky, matches = self._build(db, now, organization_id)
        return ActionIntelligenceSummaryResponse(
            total_actions=len(items), critical_actions=sum(x.priority == PriorityLevel.CRITICAL for x in items),
            high_priority_actions=sum(x.priority == PriorityLevel.HIGH for x in items), overdue_follow_ups=overdue,
            stale_leads=stale, deals_at_risk=risky, warehouse_opportunities_requiring_attention=matches,
            evaluated_at=now,
        )