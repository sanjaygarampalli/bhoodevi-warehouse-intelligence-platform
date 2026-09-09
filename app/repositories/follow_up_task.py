from sqlalchemy import and_, case, select
from sqlalchemy.orm import Session, raiseload

from app.models.follow_up_task import FollowUpTask
from app.models.lead import Lead


class FollowUpTaskRepository:
    def get_reference(self, db: Session, model, reference_id, *, lock=True):
        stmt = select(model).where(model.id == reference_id).execution_options(populate_existing=True)
        return db.scalar(stmt.with_for_update() if lock else stmt)

    def get_by_id(self, db, task_id, *, lock=False):
        return self.get_reference(db, FollowUpTask, task_id, lock=lock)

    def active_recommendation(self, db, lead_id, key):
        return db.scalar(select(FollowUpTask).where(
            FollowUpTask.lead_id == lead_id, FollowUpTask.recommendation_key == key,
            FollowUpTask.status.in_(("OPEN", "IN_PROGRESS")),
        ))

    def list_tasks(self, db, *, now, lead_id=None, deal_id=None, assigned_to_user_id=None,
                   status=None, queue=None, skip=0, limit=100):
        task = FollowUpTask
        active = task.status.in_(("OPEN", "IN_PROGRESS"))
        overdue = and_(active, task.due_at < now)
        stmt = select(task).options(raiseload("*"))
        for field, value in ((task.lead_id, lead_id), (task.deal_id, deal_id),
                             (task.assigned_to_user_id, assigned_to_user_id), (task.status, status)):
            if value is not None:
                stmt = stmt.where(field == value)
        if queue == "OPEN":
            stmt = stmt.where(active)
        elif queue == "OVERDUE":
            stmt = stmt.where(overdue)
        elif queue == "UPCOMING":
            stmt = stmt.where(active, task.due_at >= now)
        priority = case({"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}, value=task.priority, else_=4)
        return list(db.scalars(stmt.order_by(case((overdue, 0), else_=1), task.due_at, priority, task.id)
                               .offset(skip).limit(limit)))

    def save(self, db, task):
        db.add(task)
        db.flush()
        db.commit()
        db.refresh(task)
        return task

    def has_reference(self, db, entity, entity_id):
        stmt = select(FollowUpTask.id)
        if entity == "lead":
            stmt = stmt.where(FollowUpTask.lead_id == entity_id)
        elif entity == "company":
            stmt = stmt.join(Lead, Lead.id == FollowUpTask.lead_id).where(Lead.company_id == entity_id)
        elif entity == "user":
            stmt = stmt.where(FollowUpTask.assigned_to_user_id == entity_id)
        else:
            raise ValueError("Unknown task reference type")
        return db.scalar(stmt.limit(1)) is not None