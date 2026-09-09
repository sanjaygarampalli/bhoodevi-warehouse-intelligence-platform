"""Integrated, read-only opportunity (Deal) context assembled from existing modules."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.warehouse_match import WarehouseMatch
from app.schemas.opportunity import NextActionItem, OpportunitySummary
from app.services.deal import DealService
from app.services.follow_up_task import FollowUpTaskService
from app.services.lead_intelligence import LeadIntelligenceService

# Matches the project's existing list pagination cap (see Deal/Follow-up services).
_MAX_MATCHES = 100


class OpportunityService:
    """Compose one explainable, read-only business view across existing domains.

    Reuses the existing deal, follow-up task, and lead intelligence services so
    authorization, tenant scoping, and lifecycle rules are not re-implemented.
    Each related collection is loaded with a single bounded query to avoid N+1
    access against the session's lazy-loading policy.
    """

    def __init__(self) -> None:
        self._deals = DealService()
        self._intelligence = LeadIntelligenceService()
        self._tasks = FollowUpTaskService()

    def get_opportunity(self, db: Session, deal_id: int) -> OpportunitySummary:
        """Return the integrated context for a deal the current user can read.

        DealService.get_deal raises DealNotFound for missing deals and returns the
        deal with its stage/lead/requirement/match eager-loaded. Warehouse matches
        for the requirement are fetched in one bounded query. Follow-up tasks are
        limited to this deal's OPEN and IN_PROGRESS rows (bounded lists). Lead
        intelligence is derived read-only from the existing deterministic rule
        engine.
        """
        deal = self._deals.get_deal(db, deal_id)
        matches = self._requirement_matches(db, deal)
        open_tasks = self._tasks.list_tasks(db, deal_id=deal_id, status="OPEN")
        open_tasks.extend(self._tasks.list_tasks(db, deal_id=deal_id, status="IN_PROGRESS"))
        overdue = [task for task in open_tasks if task.is_overdue]
        upcoming = [task for task in open_tasks if not task.is_overdue]
        intelligence = self._intelligence.calculate_lead_score(db, deal.lead_id)
        return OpportunitySummary(
            deal=deal,
            organization=deal.organization,
            lead=deal.lead,
            requirement=deal.requirement,
            selected_warehouse_match=deal.selected_warehouse_match,
            warehouse_matches=matches,
            open_tasks=open_tasks,
            overdue_tasks=overdue,
            upcoming_tasks=upcoming,
            intelligence=intelligence,
            next_action=self._next_action(deal, open_tasks, intelligence),
            generated_at=datetime.now(timezone.utc),
        )

    def _requirement_matches(self, db: Session, deal) -> list[WarehouseMatch]:
        """Return matches for the deal's requirement in one bounded query, best first."""
        if deal.requirement is None:
            return []
        matches = (
            db.query(WarehouseMatch)
            .filter(WarehouseMatch.requirement_id == deal.requirement_id)
            .order_by(WarehouseMatch.match_score.desc(), WarehouseMatch.created_at.desc())
            .limit(_MAX_MATCHES)
            .all()
        )
        return [match for match in matches if match.requirement_id == deal.requirement_id]

    def _next_action(self, deal, open_tasks, intelligence):
        """Derive a single, deterministic, explainable next step.

        Priority order (no invented predictions):
        1. Overdue follow-up task (nearest due date) - urgent business action.
        2. Earliest upcoming open follow-up task.
        3. Lead intelligence Next-Best-Action (deterministic rule table).
        4. No actionable item.
        """
        if deal.deal_status != "OPEN" or deal.stage is None:
            return None

        overdue = [task for task in open_tasks if task.is_overdue]
        if overdue:
            task = min(overdue, key=lambda item: (item.due_at is None, item.due_at, item.id))
            return NextActionItem(
                type="OVERDUE_FOLLOW_UP",
                summary=f"Complete overdue follow-up task #{task.id}: {task.subject}",
                reason=(
                    "An open follow-up task on this deal is past its due date and "
                    "blocks progress. Complete or cancel it to unblock the pipeline."
                ),
                reference_id=task.id,
                due_at=task.due_at,
            )

        upcoming = [task for task in open_tasks if not task.is_overdue]
        if upcoming:
            task = min(upcoming, key=lambda item: (item.due_at is None, item.due_at, item.id))
            return NextActionItem(
                type="UPCOMING_FOLLOW_UP",
                summary=f"Advance follow-up task #{task.id}: {task.subject}",
                reason=(
                    "The earliest scheduled follow-up task on this deal is due soon. "
                    "Complete it to keep the deal moving through the pipeline."
                ),
                reference_id=task.id,
                due_at=task.due_at,
            )

        if intelligence is not None and intelligence.explanation is not None:
            explanation = intelligence.explanation
            return NextActionItem(
                type="LEAD_NEXT_BEST_ACTION",
                summary=explanation.action_reason,
                reason=(
                    f"Lead Next-Best-Action ({explanation.recommended_action.value}) at score "
                    f"{intelligence.total_score} (priority {intelligence.priority.value})."
                ),
                reference_id=deal.lead_id,
                due_at=None,
            )

        return None