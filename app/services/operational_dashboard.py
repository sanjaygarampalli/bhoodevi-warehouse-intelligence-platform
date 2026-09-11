"""Aggregate existing BWIP intelligence into one read-only operational view."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload
from app.models.deal import Deal
from app.models.deal_pipeline_stage import DealPipelineStage
from app.models.follow_up_task import FollowUpTask, TaskStatus, as_utc
from app.models.lead import Lead, LeadStatus
from app.models.lead_activity import LeadActivity
from app.models.requirement import Requirement, RequirementStatus
from app.models.warehouse_match import WarehouseMatch, WarehouseMatchStatus
from app.schemas.operational_dashboard import *
from app.schemas.prospect_prioritization import NextBestActionType, PriorityLevel
from app.services.lead_scoring_rules import HIGH_MATCH_SCORE, VIABLE_MATCH_SCORE
from app.services.prospect_prioritization import ProspectPrioritizationService

ACTIVE_LEAD_STATUSES = tuple(s for s in LeadStatus if s not in {LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED})

class OperationalDashboardService:
    def __init__(self, *, prioritization_service=None, clock=None):
        self.prioritization = prioritization_service or ProspectPrioritizationService()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _action(result):
        return result.next_best_action.action.value if result.next_best_action else NextBestActionType.MONITOR.value

    @classmethod
    def _reason(cls, result):
        return result.next_best_action.reason if result.next_best_action else (result.reasons[0].detail if result.reasons else "Priority evaluation completed.")

    @staticmethod
    def _name(result):
        return (result.company_name or result.lead_number) if hasattr(result, "lead_number") else result.deal_name

    def _priority_item(self, result):
        lead = hasattr(result, "lead_number")
        return PriorityDashboardItem(entity_type="lead" if lead else "opportunity", entity_id=result.lead_id if lead else result.deal_id, name=self._name(result), priority_level=result.priority_level.value, priority_score=result.priority_score, recommended_action=self._action(result), reason=self._reason(result))

    def _attention(self, leads, opportunities, tasks, now, limit):
        items = []
        for task in tasks:
            if task.status not in (TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value): continue
            due = as_utc(task.due_at)
            if due <= now:
                overdue = due < now
                items.append(AttentionItem(entity_type="follow_up", entity_id=task.id, title=task.subject, priority="URGENT" if overdue else "HIGH", recommended_action="FOLLOW_UP_OVERDUE" if overdue else "FOLLOW_UP_TODAY", reason="Assigned follow-up is overdue." if overdue else "Assigned follow-up is due today.", relevant_date=due))
        for result in leads + opportunities:
            if result.priority_level in (PriorityLevel.CRITICAL, PriorityLevel.HIGH) and self._action(result) != NextBestActionType.MONITOR.value:
                items.append(AttentionItem(entity_type="lead" if hasattr(result, "lead_number") else "opportunity", entity_id=result.lead_id if hasattr(result, "lead_number") else result.deal_id, title=self._name(result), priority=result.priority_level.value, recommended_action=self._action(result), reason=self._reason(result), relevant_date=result.evaluated_at))
        rank = {"CRITICAL": 0, "URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        return sorted(items, key=lambda x: (rank.get(x.priority, 4), x.relevant_date or now, x.entity_id))[:limit]

    def get_dashboard(self, db: Session, *, top_priorities_limit=5, recent_activity_limit=10, attention_limit=50):
        now = as_utc(self.clock()); today = now.date()
        leads = self.prioritization.list_lead_priorities(db, limit=200, offset=0, evaluated_at=now).items
        opportunities = self.prioritization.list_opportunity_priorities(db, limit=200, offset=0, evaluated_at=now).items
        rows = list(db.scalars(select(Lead).options(joinedload(Lead.company), selectinload(Lead.activities), selectinload(Lead.requirements))).all())
        tasks = list(db.scalars(select(FollowUpTask).options(joinedload(FollowUpTask.lead))).all())
        deals = list(db.scalars(select(Deal).options(joinedload(Deal.stage), joinedload(Deal.lead))).all())
        matches = list(db.scalars(select(WarehouseMatch).order_by(WarehouseMatch.match_score.desc(), WarehouseMatch.id)).all())
        activities = list(db.scalars(select(LeadActivity).order_by(LeadActivity.activity_date.desc(), LeadActivity.id.desc()).limit(recent_activity_limit)).all())
        active = [x for x in rows if x.status in ACTIVE_LEAD_STATUSES]
        open_tasks = [x for x in tasks if x.status in (TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value)]
        overdue = [x for x in open_tasks if as_utc(x.due_at) < now]
        due_today = [x for x in open_tasks if as_utc(x.due_at).date() == today]
        open_deals = [x for x in deals if x.deal_status == "OPEN"]
        at_risk = [x for x in open_deals if x.expected_close_date and x.expected_close_date < today]
        strong = [x for x in matches if x.match_score >= HIGH_MATCH_SCORE and x.status not in (WarehouseMatchStatus.REJECTED, WarehouseMatchStatus.STALE)]
        viable_leads = {x.lead_id for x in matches if x.match_score >= VIABLE_MATCH_SCORE and x.status not in (WarehouseMatchStatus.REJECTED, WarehouseMatchStatus.STALE)}
        result_by_lead = {x.lead_id: x for x in leads}
        recent_ids = {x.lead_id for x in activities if as_utc(x.activity_date) >= now - timedelta(days=30)}
        active_req_rows = list(db.scalars(select(Requirement).where(Requirement.requirement_status == RequirementStatus.ACTIVE)).all())
        matched_req = {x.requirement_id for x in matches if x.requirement_id and x.status not in (WarehouseMatchStatus.REJECTED, WarehouseMatchStatus.STALE)}
        groups = defaultdict(list)
        for deal in deals: groups[deal.stage_id].append(deal)
        stages = list(db.scalars(select(DealPipelineStage).order_by(DealPipelineStage.stage_order, DealPipelineStage.id)).all())
        pipeline_stages = [PipelineStageSummary(stage_id=s.id, stage_key=s.stage_key, stage_name=s.stage_name, stage_order=s.stage_order, active_deals=sum(d.deal_status == "OPEN" for d in groups[s.id]), total_deals=len(groups[s.id]), expected_revenue=sum((d.expected_revenue or 0) for d in groups[s.id]) or None) for s in stages]
        recent = [RecentActivityItem(entity_type="lead_activity", entity_id=a.id, lead_id=a.lead_id, activity_type=getattr(a.activity_type, "value", str(a.activity_type)), title=a.subject, occurred_at=as_utc(a.activity_date), outcome=getattr(a.outcome, "value", str(a.outcome)) if a.outcome else None) for a in activities]
        health = LeadHealthSummary(high_intelligence_leads=sum(bool(result_by_lead.get(x.id) and (result_by_lead[x.id].intelligence_score or 0) >= 75) for x in active), medium_intelligence_leads=sum(bool(result_by_lead.get(x.id) and 50 <= (result_by_lead[x.id].intelligence_score or 0) < 75) for x in active), low_intelligence_leads=sum(not result_by_lead.get(x.id) or (result_by_lead[x.id].intelligence_score or 0) < 50 for x in active), leads_with_recent_activity=len(recent_ids), leads_becoming_inactive=sum(x.id not in recent_ids for x in active), leads_without_decision_makers=sum(x.primary_decision_maker_id is None for x in active), leads_without_requirements=sum(x.id not in {r.lead_id for r in active_req_rows} for x in active), leads_needing_qualification=sum(bool(result_by_lead.get(x.id) and self._action(result_by_lead[x.id]) == NextBestActionType.QUALIFY_REQUIREMENT.value) for x in active))
        warehouse = WarehouseOpportunitySummary(strong_matches=len(strong), leads_with_matching_potential=len(viable_leads), requirements_needing_matching=sum(r.id not in matched_req for r in active_req_rows), top_opportunities=[WarehouseOpportunityItem(lead_id=m.lead_id, requirement_id=m.requirement_id, match_id=m.id, match_score=m.match_score, status=getattr(m.status, "value", str(m.status)), top_reason=m.top_reason) for m in strong[:top_priorities_limit]])
        ranked = sorted(leads + opportunities, key=lambda x: (-list(PriorityLevel).index(x.priority_level), -x.priority_score, x.lead_id if hasattr(x, "lead_number") else x.deal_id))
        return OperationalDashboard(generated_at=now, executive_summary=ExecutiveSummary(total_active_leads=len(active), critical_priority_leads=sum(x.priority_level == PriorityLevel.CRITICAL for x in leads), high_priority_leads=sum(x.priority_level == PriorityLevel.HIGH for x in leads), overdue_follow_ups=len(overdue), follow_ups_due_today=len(due_today), active_opportunities=len(open_deals), active_deals=len(open_deals), deals_at_risk=len(at_risk), strong_warehouse_matches=len(strong), new_leads=sum(x.status == LeadStatus.NEW for x in rows)), todays_attention=self._attention(leads, opportunities, tasks, now, attention_limit), pipeline_summary=PipelineSummary(stages=pipeline_stages, active_deals=len(open_deals), won_deals=sum(x.deal_status == "WON" for x in deals), lost_deals=sum(x.deal_status == "LOST" for x in deals), deals_requiring_follow_up=len({x.deal_id for x in open_tasks if x.deal_id}), potential_opportunities=len(open_deals)), lead_health=health, warehouse_opportunities=warehouse, top_priorities=[self._priority_item(x) for x in ranked[:top_priorities_limit]], recent_activity=recent)
