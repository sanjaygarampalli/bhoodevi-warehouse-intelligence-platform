from datetime import datetime, timezone

from app.models.company import Company
from app.models.deal import Deal, LostReasonCategory
from app.models.deal_stage_history import DealStageHistory
from app.models.lead import Lead
from app.models.requirement import Requirement
from app.models.user import User
from app.models.warehouse import AvailabilityStatus, Warehouse
from app.models.warehouse_match import WarehouseMatch, WarehouseMatchStatus
from app.repositories.deal import DealRepository
from app.repositories.deal_pipeline_stage import DealPipelineStageRepository
from app.schemas.deal import DealCreate, DealUpdate, DealTransition
from app.services.deal_workflow import DealConflict, DealNotFound, validate_pagination, workflow_transaction


class DealService:
    def __init__(self):
        self.repository = DealRepository()
        self.stages = DealPipelineStageRepository()

    def _reference(self, db, model, reference_id, label):
        obj = self.repository.get_reference(db, model, reference_id)
        if obj is None:
            raise DealNotFound(f"{label} not found")
        return obj

    def _actor(self, db, user_id):
        if user_id is not None:
            actor = self._reference(db, User, user_id, "User")
            if not actor.is_active:
                raise DealConflict("History actor must be active")

    def _boundaries(self, db, lead_id, requirement_id, match_id, organization_id=None, *, selecting=False):
        lead = self._reference(db, Lead, lead_id, "Lead")
        company = self._reference(db, Company, lead.company_id, "Company")
        if organization_id is not None and company.organization_id != organization_id:
            raise DealConflict("Lead company organization no longer matches Deal")
        requirement = self._reference(db, Requirement, requirement_id, "Requirement")
        if requirement.lead_id != lead_id:
            raise DealConflict("Requirement must belong to the Deal Lead")
        if match_id is not None:
            match = self._reference(db, WarehouseMatch, match_id, "Warehouse match")
            if match.lead_id != lead_id:
                raise DealConflict("Warehouse match must belong to the Deal Lead")
            if match.requirement_id is not None and match.requirement_id != requirement_id:
                raise DealConflict("Warehouse match Requirement must match the Deal Requirement")
            warehouse = self._reference(db, Warehouse, match.warehouse_id, "Warehouse")
            if selecting and (match.status in (WarehouseMatchStatus.REJECTED, WarehouseMatchStatus.STALE,
                                               WarehouseMatchStatus.CONVERTED)
                              or warehouse.availability_status not in (
                                  AvailabilityStatus.AVAILABLE, AvailabilityStatus.PARTIALLY_OCCUPIED)):
                raise DealConflict("Warehouse match is not eligible for selection")
        return company.organization_id

    def _stage(self, db, stage_id, organization_id):
        stage = self.stages.get_locked(db, stage_id)
        if stage is None:
            raise DealNotFound("Deal pipeline stage not found")
        if stage.organization_id != organization_id:
            raise DealConflict("Stage must belong to the Deal organization")
        if not stage.is_active:
            raise DealConflict("Cannot enter an inactive stage")
        return stage

    @staticmethod
    def _history(previous, target, user_id, at, reason):
        return DealStageHistory(
            from_stage_id=previous.id if previous else None,
            from_stage_key=previous.stage_key if previous else None,
            from_stage_name=previous.stage_name if previous else None,
            to_stage_id=target.id, to_stage_key=target.stage_key, to_stage_name=target.stage_name,
            changed_by_user_id=user_id, changed_at=at, change_reason=reason,
        )

    @workflow_transaction
    def create_deal(self, db, payload: DealCreate, changed_by_user_id=None):
        data = DealCreate.model_validate(payload.model_dump()).model_dump()
        organization_id = self._boundaries(db, data["lead_id"], data["requirement_id"],
                                           data["selected_warehouse_match_id"], selecting=True)
        stage = self._stage(db, data["stage_id"], organization_id)
        if stage.is_terminal:
            raise DealConflict("Create a Deal in a nonterminal stage, then explicitly close it")
        self._actor(db, changed_by_user_id)
        at = datetime.now(timezone.utc)
        deal = Deal(**data, organization_id=organization_id, stage_entered_at=at)
        return self.repository.save(db, deal, self._history(None, stage, changed_by_user_id, at, "Deal created"))

    def create_deal_in_transaction(self, db, payload: DealCreate, changed_by_user_id=None):
        """Create and flush a Deal while leaving the caller's transaction open."""
        data = DealCreate.model_validate(payload.model_dump()).model_dump()
        organization_id = self._boundaries(
            db, data["lead_id"], data["requirement_id"], data["selected_warehouse_match_id"], selecting=True,
        )
        stage = self._stage(db, data["stage_id"], organization_id)
        if stage.is_terminal:
            raise DealConflict("Create a Deal in a nonterminal stage, then explicitly close it")
        self._actor(db, changed_by_user_id)
        at = datetime.now(timezone.utc)
        deal = Deal(**data, organization_id=organization_id, stage_entered_at=at)
        db.add(deal)
        db.flush()
        history = self._history(None, stage, changed_by_user_id, at, "Deal created")
        history.deal_id = deal.id
        db.add(history)
        db.flush()
        return deal

    def get_deal(self, db, deal_id):
        deal = self.repository.get_by_id(db, deal_id)
        if deal is None:
            raise DealNotFound("Deal not found")
        return deal

    def list_deals(self, db, *, skip=0, limit=100, **filters):
        validate_pagination(skip, limit)
        return self.repository.list_deals(db, skip=skip, limit=limit, **filters)

    def get_history(self, db, deal_id, *, skip=0, limit=100):
        validate_pagination(skip, limit)
        self.get_deal(db, deal_id)
        return self.repository.history(db, deal_id, skip, limit)

    @workflow_transaction
    def update_deal(self, db, deal_id, payload: DealUpdate):
        deal = self.repository.get_by_id(db, deal_id, lock=True)
        if deal is None:
            raise DealNotFound("Deal not found")
        if deal.deal_status != "OPEN":
            raise DealConflict("Closed Deals cannot be edited or reopened")
        changes = DealUpdate.model_validate(payload.model_dump(exclude_unset=True)).model_dump(exclude_unset=True)
        match_id = changes.get("selected_warehouse_match_id", deal.selected_warehouse_match_id)
        self._boundaries(db, deal.lead_id, deal.requirement_id, match_id, deal.organization_id,
                         selecting="selected_warehouse_match_id" in changes)
        for field, value in changes.items():
            setattr(deal, field, value)
        return self.repository.save(db, deal)

    @workflow_transaction
    def transition_deal(self, db, deal_id, payload: DealTransition, changed_by_user_id=None):
        payload = DealTransition.model_validate(payload.model_dump())
        deal = self.repository.get_by_id(db, deal_id, lock=True)
        if deal is None:
            raise DealNotFound("Deal not found")
        if payload.to_stage_id == deal.stage_id:
            # A retry is a no-op, including a retry of a successful terminal transition.
            outcome_fields = (
                "lost_reason_category", "final_commercial_amount", "final_commercial_currency",
                "final_lease_duration_months", "outcome_notes", "closure_evidence_reference",
            )
            if any(getattr(payload, field) is not None for field in outcome_fields):
                if any(getattr(deal, field) != getattr(payload, field) for field in outcome_fields):
                    raise DealConflict("Closed Deal outcome evidence cannot be changed")
            db.commit()
            return self.get_deal(db, deal_id)
        if deal.deal_status != "OPEN":
            raise DealConflict("Closed Deals cannot transition or reopen")
        self._boundaries(db, deal.lead_id, deal.requirement_id, deal.selected_warehouse_match_id, deal.organization_id)
        stage = self._stage(db, payload.to_stage_id, deal.organization_id)
        outcome_fields = (
            "lost_reason_category", "final_commercial_amount", "final_commercial_currency",
            "final_lease_duration_months", "outcome_notes", "closure_evidence_reference",
        )
        if not stage.is_terminal and any(getattr(payload, field) is not None for field in outcome_fields):
            raise DealConflict("Outcome evidence is only valid when closing a Deal")
        self._actor(db, changed_by_user_id)
        previous = self.stages.get_by_id(db, deal.stage_id)
        at = datetime.now(timezone.utc)
        history = self._history(previous, stage, changed_by_user_id, at, payload.change_reason)
        deal.stage_id = stage.id
        deal.stage_entered_at = at
        if stage.is_terminal:
            deal.deal_status = "WON" if stage.is_won else "LOST"
            deal.closed_at = at
            deal.closed_reason = payload.change_reason
            deal.lost_reason_category = payload.lost_reason_category if stage.is_lost else None
            deal.final_commercial_amount = payload.final_commercial_amount
            deal.final_commercial_currency = payload.final_commercial_currency
            deal.final_lease_duration_months = payload.final_lease_duration_months
            deal.outcome_notes = payload.outcome_notes
            deal.closure_evidence_reference = payload.closure_evidence_reference
        return self.repository.save(db, deal, history)