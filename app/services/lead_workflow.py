"""Orchestration service for the lead-to-deal business workflow.

Coordinates qualification, opportunity creation, and pipeline seeding
across the existing domain services.  Does NOT duplicate business logic
already present in the individual services.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.lead import LeadStatus
from app.models.requirement import RequirementStatus
from app.models.warehouse_match import WarehouseMatchStatus
from app.schemas.lead_workflow import (
    CreateOpportunityRequest,
    CreateOpportunityResponse,
    LeadTransitionRequest,
    LeadTransitionResponse,
    QualifyLeadResponse,
    SeedPipelineResponse,
)
from app.services.deal import DealService
from app.services.deal_pipeline_stage import DealPipelineStageService
from app.services.lead import LeadService
from app.services.requirement import RequirementService
from app.services.warehouse_match import WarehouseMatchService
from app.services.deal_workflow import DealConflict, DealNotFound


# ---------------------------------------------------------------------------
# Default pipeline definition — six stages matching the BWIP sales process.
# ---------------------------------------------------------------------------
_DEFAULT_STAGES = (
    ("QUALIFICATION",    "Qualification",     0,  False, False, False),
    ("POSITIONING",      "Positioning",       1,  False, False, False),
    ("NEGOTIATION",      "Negotiation",       2,  False, False, False),
    ("CLOSED_WON",       "Closed Won",        3,  True,  True,  False),
    ("CLOSED_LOST",      "Closed Lost",       4,  True,  False, True),
)

# ---------------------------------------------------------------------------
# Lead lifecycle state machine — valid status transitions.
#
# Each entry lists the set of statuses that are valid to transition FROM
# for a given target status.  Terminal states (WON, LOST, DISQUALIFIED)
# may only be reached through dedicated endpoints (qualify/disqualify) or
# automatically via deal-closure integration.
# ---------------------------------------------------------------------------
_LEAD_LIFECYCLE: dict[str, frozenset[str]] = {
    "NEW": frozenset(),
    "DISCOVERED": frozenset({"NEW"}),
    "CONTACTED": frozenset({"NEW", "DISCOVERED"}),
    "QUALIFIED": frozenset({"NEW", "DISCOVERED", "CONTACTED"}),
    "POSITIONED": frozenset({"QUALIFIED"}),
    "NEGOTIATING": frozenset({"POSITIONED"}),
    "DORMANT": frozenset({"NEW", "DISCOVERED", "CONTACTED", "QUALIFIED", "POSITIONED", "NEGOTIATING"}),
}
# Terminal statuses have dedicated endpoints and are not in _LEAD_LIFECYCLE
# for manual transitions.
_LEAD_TERMINAL = frozenset({"WON", "LOST", "DISQUALIFIED"})


class LeadWorkflowService:
    """Orchestrate cross-domain workflow steps.

    Each public method accepts a clean session (no pending changes) and
    returns a domain result or raises a descriptive ``ValueError`` /
    ``LookupError``.
    """

    def __init__(self) -> None:
        self._leads = LeadService()
        self._requirements = RequirementService()
        self._matches = WarehouseMatchService()
        self._deals = DealService()
        self._stages = DealPipelineStageService()

    # ------------------------------------------------------------------
    # A — Qualify a lead
    # ------------------------------------------------------------------

    def qualify_lead(self, db: Session, lead_id: int) -> QualifyLeadResponse:
        """Transition a NEW/DISCOVERED lead to QUALIFIED after validating
        prerequisites.

        Prerequisites (matching the scoring rule engine's eligibility):
        * The lead must exist and be in a qualifying state.
        * The lead's company must have at least one non-disqualified
          decision maker.
        * The lead must have at least one active requirement.

        Returns the updated lead or raises.
        """
        if db.new or db.dirty or db.deleted:
            raise ValueError(
                "Qualification requires a session without pending changes"
            )

        lead = self._leads.get_lead_by_id(db, lead_id)
        if lead is None:
            raise LookupError("Lead not found")

        if lead.status in (
            LeadStatus.WON,
            LeadStatus.LOST,
            LeadStatus.DISQUALIFIED,
            LeadStatus.DORMANT,
        ):
            raise ValueError(
                f"Cannot qualify a lead with status {lead.status.value}"
            )

        if lead.status == LeadStatus.QUALIFIED:
            return QualifyLeadResponse(
                id=lead.id, lead_number=lead.lead_number,
                status=lead.status.value, company_id=lead.company_id,
                previous_status=lead.status.value,
            )

        previous = lead.status.value

        # Prerequisite 1: company has at least one non-disqualified contact.
        if not lead.company or not lead.company.decision_makers:
            raise ValueError(
                "Lead company must have at least one decision maker "
                "before qualification"
            )
        eligible_contacts = [
            dm for dm in lead.company.decision_makers
            if dm.decision_maker_status.value != "DISQUALIFIED"
        ]
        if not eligible_contacts:
            raise ValueError(
                "Lead company must have at least one non-disqualified "
                "decision maker before qualification"
            )

        # Prerequisite 2: at least one active requirement.
        active_reqs = [
            r for r in lead.requirements
            if r.requirement_status == RequirementStatus.ACTIVE
        ]
        if not active_reqs:
            raise ValueError(
                "Lead must have at least one active requirement "
                "before qualification"
            )

        lead.status = LeadStatus.QUALIFIED
        lead.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(lead)

        return QualifyLeadResponse(
            id=lead.id, lead_number=lead.lead_number,
            status=lead.status.value, company_id=lead.company_id,
            previous_status=previous,
        )
# ------------------------------------------------------------------
    # B — Create opportunity (Deal) from a qualified lead
    # ------------------------------------------------------------------

    def create_opportunity(
        self,
        db: Session,
        lead_id: int,
        payload: CreateOpportunityRequest,
        *,
        changed_by_user_id: int | None = None,
    ) -> CreateOpportunityResponse:
        """Create a Deal from a qualified lead's best active requirement
        and best eligible warehouse match.

        The lead must be in QUALIFIED status.  The best active requirement
        (highest priority_score, then newest) and the best eligible
        warehouse match (highest match_score) are selected automatically.

        Raises ``LookupError`` or ``ValueError`` when prerequisites are
        not satisfied.
        """
        if db.new or db.dirty or db.deleted:
            raise ValueError(
                "Opportunity creation requires a session without "
                "pending changes"
            )

        lead = self._leads.get_lead_by_id(db, lead_id)
        if lead is None:
            raise LookupError("Lead not found")

        if lead.status != LeadStatus.QUALIFIED:
            raise ValueError(
                f"Lead must be QUALIFIED before creating an opportunity; "
                f"current status is {lead.status.value}"
            )

        # Pick the best active requirement (or the explicitly requested one).
        if payload.requirement_id is not None:
            requirement = self._requirements.get_requirement_by_id(
                db, payload.requirement_id,
            )
            if requirement is None:
                raise LookupError(
                    f"Specified requirement {payload.requirement_id} not found"
                )
            if requirement.lead_id != lead_id:
                raise ValueError(
                    "Specified requirement does not belong to this lead"
                )
            if requirement.requirement_status != RequirementStatus.ACTIVE:
                raise ValueError(
                    "Specified requirement is not ACTIVE"
                )
        else:
            active_reqs = [
                r for r in lead.requirements
                if r.requirement_status == RequirementStatus.ACTIVE
            ]
            if not active_reqs:
                raise ValueError(
                    "Lead has no active requirement; cannot create opportunity"
                )

            def _req_key(r):
                return (
                    r.priority_score if r.priority_score is not None else 0,
                    r.requirement_score if r.requirement_score is not None else 0,
                    r.created_at.timestamp() if r.created_at else 0,
                    r.id,
                )

            requirement = max(active_reqs, key=_req_key)
# Pick the best eligible warehouse match for this requirement.
        matches = self._matches.list_matches_for_requirement(
            db, requirement.id, limit=100, offset=0,
        )
        eligible_matches = [
            m for m in matches
            if m.status not in (
                WarehouseMatchStatus.REJECTED,
                WarehouseMatchStatus.STALE,
                WarehouseMatchStatus.CONVERTED,
            )
        ]
        selected_match = (
            max(eligible_matches, key=lambda m: (m.match_score, m.id))
            if eligible_matches
            else None
        )

        # Build DealCreate and delegate to DealService.
        from app.schemas.deal import DealCreate

        deal_payload = DealCreate(
            deal_name=payload.deal_name,
            lead_id=lead_id,
            requirement_id=requirement.id,
            stage_id=payload.stage_id,
            selected_warehouse_match_id=(
                selected_match.id if selected_match else None
            ),
            expected_revenue=payload.expected_revenue,
            currency=payload.currency,
            expected_close_date=payload.expected_close_date,
            notes=payload.notes,
        )

        try:
            deal = self._deals.create_deal(
                db, deal_payload, changed_by_user_id=changed_by_user_id,
            )
        except (DealConflict, DealNotFound) as exc:
            raise ValueError(str(exc)) from exc

        # Advance the lead from QUALIFIED to POSITIONED to reflect the
        # new opportunity in the pipeline.
        if lead.status == LeadStatus.QUALIFIED:
            from app.schemas.lead import LeadUpdate
            lead_update = LeadUpdate.model_validate({"status": LeadStatus.POSITIONED.value})
            updated_lead = self._leads.update_lead(db, lead_id, lead_update)
            if updated_lead is None:
                raise ValueError("Failed to advance lead status to POSITIONED")
            lead = updated_lead

        # Create an initial follow-up task for the next business step.
        from datetime import timedelta
        from app.schemas.follow_up_task import FollowUpTaskCreate
        from app.models.follow_up_task import TaskType
        initial_task_payload = FollowUpTaskCreate(
            lead_id=lead_id,
            deal_id=deal.id,
            subject=f"Present proposal for {deal.deal_name}",
            description=(
                "Auto-generated on opportunity creation. Prepare and present "
                "the warehouse proposal to the customer."
            ),
            task_type=TaskType.PROPOSAL_FOLLOWUP,
            priority="HIGH" if (
                deal.expected_revenue is not None
                and deal.expected_revenue > 0
            ) else "MEDIUM",
            due_at=datetime.now(timezone.utc)
            + timedelta(days=7),
        )
        from app.services.follow_up_task import FollowUpTaskService
        initial_task_id = None
        try:
            initial_task = FollowUpTaskService().create_task(
                db, initial_task_payload,
            )
            initial_task_id = initial_task.id
        except Exception:
            # Non-blocking: a failed initial task creation should not
            # roll back the successful deal creation.
            db.commit()

        return CreateOpportunityResponse(
            deal_id=deal.id,
            deal_name=deal.deal_name,
            lead_id=deal.lead_id,
            requirement_id=deal.requirement_id,
            selected_warehouse_match_id=deal.selected_warehouse_match_id,
            organization_id=deal.organization_id,
            stage_id=deal.stage_id,
            deal_status=deal.deal_status,
            lead_status=lead.status.value if lead else "UNKNOWN",
            initial_task_id=initial_task_id,
            created_at=deal.created_at,
        )

    # ------------------------------------------------------------------
    # C — Disqualify a lead with a reason
    # ------------------------------------------------------------------

    def disqualify_lead(
        self, db: Session, lead_id: int, reason: str,
    ) -> QualifyLeadResponse:
        """Transition a non-terminal lead to DISQUALIFIED with a reason.

        A lead can be disqualified only if it is not already in a terminal
        state (WON, LOST, DISQUALIFIED, DORMANT).  The reason is recorded
        on the lead for auditability.

        Raises ``LookupError`` if the lead does not exist.
        Raises ``ValueError`` if the lead is already in a terminal state.
        """
        if db.new or db.dirty or db.deleted:
            raise ValueError(
                "Disqualification requires a session without pending changes"
            )

        lead = self._leads.get_lead_by_id(db, lead_id)
        if lead is None:
            raise LookupError("Lead not found")

        if lead.status in (
            LeadStatus.WON,
            LeadStatus.LOST,
            LeadStatus.DISQUALIFIED,
            LeadStatus.DORMANT,
        ):
            raise ValueError(
                f"Cannot disqualify a lead with status {lead.status.value}"
            )

        from app.schemas.lead import LeadUpdate

        previous_status = lead.status.value
        lead_update = LeadUpdate(
            status=LeadStatus.DISQUALIFIED,
            disqualified_reason=reason,
        )
        updated_lead = self._leads.update_lead(db, lead_id, lead_update)
        if updated_lead is None:
            raise ValueError("Failed to disqualify lead")

        return QualifyLeadResponse(
            id=updated_lead.id,
            lead_number=updated_lead.lead_number,
            status=updated_lead.status.value,
            company_id=updated_lead.company_id,
            previous_status=previous_status,
            disqualified_reason=updated_lead.disqualified_reason,
        )

    # ------------------------------------------------------------------
    # E — Transition lead status (non-terminal lifecycle)
    # ------------------------------------------------------------------

    def transition_lead_status(
        self, db: Session, lead_id: int, payload: LeadTransitionRequest,
    ) -> LeadTransitionResponse:
        """Transition a lead through its lifecycle state machine.

        Validates the requested transition against ``_LEAD_LIFECYCLE`` and
        rejects terminal-status transitions (WON, LOST, DISQUALIFIED) as
        those require dedicated endpoints or deal-automation hooks.

        Records ``previous_status`` for auditability and optionally stores
        the reason in ``closed_reason`` (or ``disqualified_reason`` for
        DISQUALIFIED, which is handled separately).

        Raises ``ValueError`` for invalid transitions and ``LookupError``
        when the lead is not found.
        """
        if db.new or db.dirty or db.deleted:
            raise ValueError(
                "Lead transition requires a session without pending changes"
            )

        from app.schemas.lead import LeadUpdate

        target = payload.new_status.upper().strip()
        if target in _LEAD_TERMINAL:
            raise ValueError(
                f"Cannot transition to terminal status '{target}' through "
                "this endpoint. Use the dedicated qualify/disqualify "
                "endpoints instead."
            )

        allowed_from = _LEAD_LIFECYCLE.get(target)
        if allowed_from is None:
            raise ValueError(
                f"Unknown lead status '{payload.new_status}'. "
                f"Valid values: {', '.join(sorted(_LEAD_LIFECYCLE))}."
            )

        lead = self._leads.get_lead_by_id(db, lead_id)
        if lead is None:
            raise LookupError("Lead not found")

        if lead.status in (LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED):
            raise ValueError(
                f"Cannot transition a lead with terminal status "
                f"'{lead.status.value}'"
            )

        current = lead.status.value
        if current == target:
            # Same-status transition is a no-op / idempotent.
            return LeadTransitionResponse(
                id=lead.id,
                lead_number=lead.lead_number,
                status=current,
                company_id=lead.company_id,
                previous_status=current,
                transition_reason=payload.reason,
            )

        if current not in allowed_from:
            raise ValueError(
                f"Cannot transition lead from '{current}' to '{target}'. "
                f"Allowed source statuses for '{target}': "
                f"{', '.join(sorted(allowed_from))}."
            )

        previous_status = current
        lead_update = LeadUpdate(
            status=LeadStatus(target),
            closed_reason=payload.reason,
        )
        updated_lead = self._leads.update_lead(db, lead_id, lead_update)
        if updated_lead is None:
            raise ValueError("Failed to transition lead status")

        return LeadTransitionResponse(
            id=updated_lead.id,
            lead_number=updated_lead.lead_number,
            status=updated_lead.status.value,
            company_id=updated_lead.company_id,
            previous_status=previous_status,
            transition_reason=payload.reason,
        )

    # ------------------------------------------------------------------
    # F — Advance lead status based on deal outcome (automation hook)
    # ------------------------------------------------------------------

    def _advance_lead_on_deal_closure(
        self, db: Session, deal,
    ) -> None:
        """Automatically advance the lead status to WON or LOST when a
        deal reaches a terminal outcome.

        Called by the deal transition flow; does NOT commit (the caller
        owns the transaction).  This is intentionally non-blocking —
        if the lead cannot be advanced (e.g. it's already terminal), the
        error is silently swallowed because the deal outcome takes
        precedence over lead-level validation.

        Matches POSITIONED or NEGOTIATING leads to their corresponding
        terminal outcome.
        """
        if deal.deal_status == "OPEN":
            return

        from app.schemas.lead import LeadUpdate

        lead = self._leads.get_lead_by_id(db, deal.lead_id)
        if lead is None:
            return  # Lead gone — deal outcome still recorded.

        # Only advance if the lead is in an appropriate pre-closure state.
        if lead.status not in (LeadStatus.POSITIONED, LeadStatus.NEGOTIATING):
            return

        if deal.deal_status == "WON":
            target = LeadStatus.WON
        elif deal.deal_status == "LOST":
            target = LeadStatus.LOST
        else:
            return  # Unknown status, do nothing.

        lead_update = LeadUpdate(
            status=target,
            closed_reason=deal.closed_reason,
        )
        self._leads.update_lead(db, deal.lead_id, lead_update)
        # Note: No extra commit — the caller's transaction owns persistence.

    # ------------------------------------------------------------------
    # H — Transition deal with automatic lead advancement
    # ------------------------------------------------------------------

    def transition_deal_with_lead(
        self, db: Session, deal_id: int,
        payload,
        changed_by_user_id: int | None = None,
    ):
        """Transition a deal to a new stage and, when the deal reaches a
        terminal outcome (WON/LOST), automatically advance the associated
        lead status.

        Delegates to ``DealService.transition_deal`` for the core logic
        and then applies the lead lifecycle automation hook
        ``_advance_lead_on_deal_closure``.

        Returns the updated ``Deal`` (same return type as the deal service).
        """
        deal = self._deals.transition_deal(
            db, deal_id, payload,
            changed_by_user_id=changed_by_user_id,
        )
        # After a successful transition, sync the lead status if the deal
        # has been closed.  The deal service has already committed.
        self._advance_lead_on_deal_closure(db, deal)
        return deal

    # ------------------------------------------------------------------
    # I — Seed default pipeline stages idempotently
    # ------------------------------------------------------------------

    def seed_default_pipeline(
        self, db: Session, organization_id: int,
    ) -> SeedPipelineResponse:
        """Create the standard set of deal pipeline stages for an
        organization if they do not already exist.

        This is idempotent: stages that already exist (matched by
        ``stage_key``) are not duplicated.
        """
        if db.new or db.dirty or db.deleted:
            raise ValueError(
                "Pipeline seeding requires a session without pending changes"
            )

        # Check organization exists.
        from app.models.organization import Organization

        org = db.get(Organization, organization_id)
        if org is None:
            raise LookupError("Organization not found")

        created = 0
        for key, name, order, terminal, won, lost in _DEFAULT_STAGES:
            existing = [
                s for s in self._stages.list_stages(
                    db, organization_id=organization_id,
                )
                if s.stage_key == key
            ]
            if existing:
                continue

            from app.schemas.deal_pipeline_stage import DealPipelineStageCreate

            stage_payload = DealPipelineStageCreate(
                organization_id=organization_id,
                stage_name=name,
                stage_key=key,
                stage_order=order,
                is_terminal=terminal,
                is_won=won,
                is_lost=lost,
            )
            self._stages.create_stage(db, stage_payload)
            created += 1

        final_count = len(
            self._stages.list_stages(
                db, organization_id=organization_id,
            )
        )

        return SeedPipelineResponse(
            stages_created=created,
            stages_present=final_count,
            organization_id=organization_id,
        )