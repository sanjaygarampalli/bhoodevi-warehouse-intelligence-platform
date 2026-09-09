"""Shared transaction boundary and narrow protections for Deal source records."""
from functools import wraps

from sqlalchemy.exc import IntegrityError

from app.repositories.deal import DealRepository


class DealConflict(ValueError):
    pass


class DealNotFound(LookupError):
    pass


def workflow_transaction(method):
    @wraps(method)
    def wrapped(self, db, *args, **kwargs):
        if db.new or db.dirty or db.deleted:
            raise DealConflict("Deal workflow requires a session without pending changes")
        try:
            return method(self, db, *args, **kwargs)
        except IntegrityError as exc:
            db.rollback()
            raise DealConflict("Conflicting or referenced data; check stage key/order and duplicate open Requirement deals") from exc
        except Exception:
            db.rollback()
            raise
    return wrapped


def validate_pagination(skip, limit):
    if skip < 0 or not 1 <= limit <= 100:
        raise DealConflict("Pagination requires skip >= 0 and limit between 1 and 100")


def protect_deal_reference(db, entity, entity_id):
    if DealRepository().has_reference(db, entity, entity_id):
        raise DealConflict(f"Cannot delete or reassign {entity}: it is referenced by a Deal")