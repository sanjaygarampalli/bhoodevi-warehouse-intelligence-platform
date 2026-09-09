from datetime import datetime, timezone

from app.models.company import Company
from app.models.deal import Deal
from app.models.follow_up_task import FollowUpTask, TaskStatus, TaskType, as_utc
from app.models.lead import Lead
from app.models.user import User
from app.repositories.follow_up_task import FollowUpTaskRepository
from app.schemas.follow_up_task import (
    FollowUpTaskCreate, FollowUpTaskResponse, FollowUpTaskUpdate, NextActionTaskCreate,
    TaskCancellation, TaskCompletion,
)
from app.schemas.lead_intelligence import LeadNextAction
from app.services.follow_up_workflow import TaskConflict, TaskNotFound, task_transaction
from app.services.lead_intelligence import LeadIntelligenceService


class FollowUpTaskService:
    def __init__(self, *, clock=None):
        self.repository = FollowUpTaskRepository()
        self.intelligence = LeadIntelligenceService()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def _present(self, task, now=None):
        result = FollowUpTaskResponse.model_validate(task)
        result.is_overdue = task.overdue_at(now if now is not None else self.clock())
        return result

    def _reference(self, db, model, reference_id, label):
        obj = self.repository.get_reference(db, model, reference_id)
        if obj is None:
            raise TaskNotFound(f"{label} not found")
        return obj

    def _boundaries(self, db, lead_id, deal_id):
        # Match the existing Deal update order: Deal -> Lead -> Company.
        deal = self._reference(db, Deal, deal_id, "Deal") if deal_id is not None else None
        lead = self._reference(db, Lead, lead_id, "Lead")
        company = self._reference(db, Company, lead.company_id, "Company")
        if deal is not None and (deal.lead_id != lead.id or deal.organization_id != company.organization_id):
            raise TaskConflict("Deal must belong to the task Lead and its organization")

    def _assignment(self, db, user_id):
        if user_id is not None:
            user = self._reference(db, User, user_id, "Assigned user")
            if not user.is_active:
                raise TaskConflict("Assigned user must be active")

    def _task(self, db, task_id, *, lock=False):
        task = self.repository.get_by_id(db, task_id, lock=lock)
        if task is None:
            raise TaskNotFound("Follow-up Task not found")
        return task

    @task_transaction
    def create_task(self, db, payload: FollowUpTaskCreate):
        data = FollowUpTaskCreate.model_validate(payload.model_dump()).model_dump()
        self._boundaries(db, data["lead_id"], data["deal_id"])
        self._assignment(db, data["assigned_to_user_id"])
        now = as_utc(self.clock())
        task = FollowUpTask(**data, created_at=now, updated_at=now)
        return self._present(self.repository.save(db, task), now)

    def get_task(self, db, task_id):
        return self._present(self._task(db, task_id))

    def list_tasks(self, db, *, skip=0, limit=100, lead_id=None, deal_id=None,
                   assigned_to_user_id=None, status=None, queue=None):
        if skip < 0 or not 1 <= limit <= 100:
            raise TaskConflict("Pagination requires skip >= 0 and limit between 1 and 100")
        if queue not in (None, "OPEN", "OVERDUE", "UPCOMING"):
            raise TaskConflict("Unknown operational queue")
        if status is not None and status not in {s.value for s in TaskStatus}:
            raise TaskConflict("Unknown task status")
        if any(value is not None and value <= 0 for value in (lead_id, deal_id, assigned_to_user_id)):
            raise TaskConflict("Filter IDs must be positive")
        now = as_utc(self.clock())
        tasks = self.repository.list_tasks(db, now=now, skip=skip, limit=limit, lead_id=lead_id,
                                          deal_id=deal_id, assigned_to_user_id=assigned_to_user_id,
                                          status=status, queue=queue)
        return [self._present(task, now) for task in tasks]

    @task_transaction
    def update_task(self, db, task_id, payload: FollowUpTaskUpdate):
        changes = FollowUpTaskUpdate.model_validate(payload.model_dump(exclude_unset=True)).model_dump(exclude_unset=True)
        task = self._task(db, task_id, lock=True)
        if task.status not in ("OPEN", "IN_PROGRESS"):
            raise TaskConflict("Terminal tasks cannot be edited or reopened")
        if task.status == "IN_PROGRESS" and changes.get("status") == "OPEN":
            raise TaskConflict("IN_PROGRESS tasks cannot transition back to OPEN")
        self._boundaries(db, task.lead_id, task.deal_id)
        if "assigned_to_user_id" in changes:
            self._assignment(db, changes["assigned_to_user_id"])
        for field, value in changes.items():
            setattr(task, field, value)
        task.updated_at = as_utc(self.clock())
        return self._present(self.repository.save(db, task))

    def _close(self, db, task_id, status, note):
        task = self._task(db, task_id, lock=True)
        field = "completion_notes" if status == "COMPLETED" else "cancellation_reason"
        if task.status == status:
            if note is not None and note != getattr(task, field):
                raise TaskConflict("Terminal retry cannot replace the recorded note")
            db.commit()
            return self._present(task)
        if task.status not in ("OPEN", "IN_PROGRESS"):
            raise TaskConflict("Terminal tasks cannot change outcome or reopen")
        self._boundaries(db, task.lead_id, task.deal_id)
        now = as_utc(self.clock())
        task.status = status
        setattr(task, field, note)
        setattr(task, "completed_at" if status == "COMPLETED" else "cancelled_at", now)
        task.updated_at = now
        return self._present(self.repository.save(db, task), now)

    @task_transaction
    def complete_task(self, db, task_id, payload: TaskCompletion):
        data = TaskCompletion.model_validate(payload.model_dump())
        return self._close(db, task_id, "COMPLETED", data.completion_notes)

    @task_transaction
    def cancel_task(self, db, task_id, payload: TaskCancellation):
        data = TaskCancellation.model_validate(payload.model_dump())
        return self._close(db, task_id, "CANCELLED", data.cancellation_reason)

    @task_transaction
    def create_from_next_action(self, db, lead_id, payload: NextActionTaskCreate):
        data = NextActionTaskCreate.model_validate(payload.model_dump())
        self._boundaries(db, lead_id, None)
        self._assignment(db, data.assigned_to_user_id)
        # Refresh previously loaded graphs in a clean session, not just stale snapshots.
        db.expire_all()
        result = self.intelligence.calculate_lead_score(db, lead_id)
        if result is None:
            raise TaskNotFound("Lead not found")
        context = result.explanation
        if context is None or context.recommended_action == LeadNextAction.MONITOR:
            raise TaskConflict("No actionable Next Best Action; MONITOR does not schedule outreach")
        action = context.recommended_action
        existing = self.repository.active_recommendation(db, lead_id, action.value)
        if existing is not None:
            # Retry never silently changes the existing deadline, assignee or evidence.
            db.commit()
            return self._present(existing)
        now = as_utc(self.clock())
        task = FollowUpTask(
            lead_id=lead_id, subject=action.value.replace("_", " ").title(),
            description=context.action_reason, task_type=TaskType.REVIEW, priority=result.priority,
            due_at=data.due_at, assigned_to_user_id=data.assigned_to_user_id,
            recommendation_key=action.value,
            recommendation_context={**context.model_dump(mode="json"),
                                    "calculated_at": result.calculated_at.isoformat(),
                                    "scoring_version": result.scoring_version, "total_score": result.total_score},
            created_at=now, updated_at=now,
        )
        # REVIEW is deliberate: the recommendation does not select a verified channel.
        return self._present(self.repository.save(db, task), now)