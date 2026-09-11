"""Workflow endpoints that orchestrate the lead-to-deal business journey."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.deal import DealResponse, DealTransition
from app.schemas.lead_workflow import (
    CreateOpportunityRequest,
    CreateOpportunityResponse,
    DisqualifyLeadRequest,
    LeadTransitionRequest,
    LeadTransitionResponse,
    QualifyLeadResponse,
    SeedPipelineRequest,
    SeedPipelineResponse,
)
from app.services.lead_workflow import LeadWorkflowService

router = APIRouter(
    prefix="/workflow",
    tags=["Workflow"],
)

workflow_service = LeadWorkflowService()


def _map_error(exc: Exception) -> HTTPException:
    """Translate service-level errors into HTTP responses."""
    if isinstance(exc, LookupError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected workflow error",
    )


@router.post(
    "/leads/{lead_id}/qualify",
    response_model=QualifyLeadResponse,
)
def qualify_lead(
    lead_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Validate and transition a lead to QUALIFIED status."""
    try:
        return workflow_service.qualify_lead(db, lead_id)
    except (ValueError, LookupError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/leads/{lead_id}/opportunities",
    response_model=CreateOpportunityResponse,
)
def create_opportunity(
    lead_id: int,
    payload: CreateOpportunityRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Create a Deal (opportunity) from a qualified lead's best active
    requirement and best eligible warehouse match.
    """
    try:
        return workflow_service.create_opportunity(
            db,
            lead_id,
            payload,
            changed_by_user_id=current_user.id,
        )
    except (ValueError, LookupError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/leads/{lead_id}/disqualify",
    response_model=QualifyLeadResponse,
)
def disqualify_lead(
    lead_id: int,
    payload: DisqualifyLeadRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Disqualify a lead with a reason. Validates the lead is not already
    in a terminal state before transitioning to DISQUALIFIED.
    """
    try:
        return workflow_service.disqualify_lead(
            db, lead_id, payload.reason,
        )
    except (ValueError, LookupError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/leads/{lead_id}/transition",
    response_model=LeadTransitionResponse,
)
def transition_lead_status(
    lead_id: int,
    payload: LeadTransitionRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Transition a lead to a new lifecycle status with validation.

    Validates the requested transition against the lead lifecycle state
    machine.  For example, ``NEW → DISCOVERED`` or ``CONTACTED → QUALIFIED``
    are valid; ``NEW → NEGOTIATING`` is rejected without ``force``.

    Terminal-status transitions (WON, LOST, DISQUALIFIED) are not permitted
    through this endpoint; use the dedicated qualify/disqualify endpoints
    or this endpoint for non-terminal transitions only.
    """
    try:
        return workflow_service.transition_lead_status(
            db, lead_id, payload,
        )
    except (ValueError, LookupError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/deals/{deal_id}/transition",
    response_model=DealResponse,
)
def transition_deal_with_lead_advancement(
    deal_id: int,
    payload: DealTransition,
    db=Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Transition a deal and automatically advance the associated lead
    status when the deal reaches a terminal outcome.

    Wraps the standard deal transition (``POST /deals/{deal_id}/transition``)
    and adds lead lifecycle automation:

    * ``CLOSED_WON``  → lead → ``WON``
    * ``CLOSED_LOST`` → lead → ``LOST``

    The lead is only advanced if its current status is ``POSITIONED`` or
    ``NEGOTIATING``; otherwise the lead status is left unchanged.
    """
    try:
        return workflow_service.transition_deal_with_lead(
            db, deal_id, payload,
            changed_by_user_id=current_user.id,
        )
    except (ValueError, LookupError) as exc:
        raise _map_error(exc) from exc


@router.post(
    "/organizations/{organization_id}/pipeline/seed",
    response_model=SeedPipelineResponse,
)
def seed_default_pipeline(
    organization_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Idempotently create default deal pipeline stages for an organization."""
    try:
        return workflow_service.seed_default_pipeline(db, organization_id)
    except (ValueError, LookupError) as exc:
        raise _map_error(exc) from exc
