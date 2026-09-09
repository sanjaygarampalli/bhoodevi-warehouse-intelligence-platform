from functools import wraps

from sqlalchemy.exc import IntegrityError

from app.repositories.follow_up_task import FollowUpTaskRepository


class TaskConflict(ValueError):
    pass


class TaskNotFound(LookupError):
    pass


def task_transaction(method):
    @wraps(method)
    def wrapped(self, db, *args, **kwargs):
        if db.new or db.dirty or db.deleted:
            raise TaskConflict("Task workflow requires a session without pending changes")
        try:
            return method(self, db, *args, **kwargs)
        except IntegrityError as exc:
            db.rollback()
            raise TaskConflict("Conflicting task references or duplicate active recommendation; retry after refreshing") from exc
        except Exception:
            db.rollback()
            raise
    return wrapped


def protect_task_reference(db, entity, entity_id):
    if FollowUpTaskRepository().has_reference(db, entity, entity_id):
        raise TaskConflict(f"Cannot delete or reassign {entity}: referenced by a Follow-up Task")