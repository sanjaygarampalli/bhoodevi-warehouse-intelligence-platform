from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.market_signal import (
    DemandStrength,
    MarketSignal,
    MarketSignalConfidence,
    MarketSignalStatus,
    MarketSignalType,
    RequirementCandidate,
    RequirementCandidateStatus,
)
from app.models.user import User
from app.schemas.market_signal import (
    MarketSignalAssessmentResponse,
    MarketSignalCreate,
    MarketSignalEvidenceCreate,
    MarketSignalEvidenceResponse,
    MarketSignalEvidenceUpdate,
    MarketSignalResponse,
    MarketSignalTransition,
    MarketSignalUpdate,
    RequirementCandidateResponse,
    RequirementCandidateTransition,
    RequirementCandidateUpdate,
)
from app.services.market_signal_intelligence import (
    EvidenceNotFound,
    MarketSignalIntelligenceService,
    MarketSignalNotFound,
    RequirementCandidateNotFound,
)
from app.services.organization_access import require_organization_access, require_organization_write

router = APIRouter(prefix="/market-signals", tags=["Market Signals"])
service = MarketSignalIntelligenceService()


def signal_or_404(db: Session, signal_id: int) -> MarketSignal:
    signal = service.get_signal(db, signal_id)
    if signal is None:
        raise MarketSignalNotFound("Market signal not found")
    return signal


def candidate_or_404(db: Session, candidate_id: int) -> RequirementCandidate:
    candidate = service.get_candidate(db, candidate_id)
    if candidate is None:
        raise RequirementCandidateNotFound("Requirement candidate not found")
    return candidate


@router.get("", response_model=list[MarketSignalResponse])
def list_market_signals(
    organization_id: int = Query(..., gt=0),
    company_id: int | None = Query(default=None, gt=0),
    signal_type: MarketSignalType | None = None,
    signal_status: MarketSignalStatus | None = Query(default=None, alias="status"),
    confidence_level: MarketSignalConfidence | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_organization_access(db, current_user, organization_id)
    return service.list_signals(db, organization_id, company_id=company_id, signal_type=signal_type, status=signal_status, confidence_level=confidence_level)


@router.post("", response_model=MarketSignalResponse, status_code=status.HTTP_201_CREATED)
def create_market_signal(data: MarketSignalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_organization_write(db, current_user, data.organization_id)
    try:
        return service.create_signal(db, data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{signal_id}", response_model=MarketSignalResponse)
def get_market_signal(signal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_access(db, current_user, signal.organization_id)
    return signal


@router.patch("/{signal_id}", response_model=MarketSignalResponse)
def update_market_signal(signal_id: int, data: MarketSignalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_write(db, current_user, signal.organization_id)
    try:
        return service.update_signal(db, signal, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{signal_id}/transition", response_model=MarketSignalResponse)
def transition_market_signal(signal_id: int, data: MarketSignalTransition, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_write(db, current_user, signal.organization_id)
    return service.transition_signal(db, signal, data.target_status)


@router.get("/{signal_id}/evidence", response_model=list[MarketSignalEvidenceResponse])
def list_signal_evidence(signal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_access(db, current_user, signal.organization_id)
    return service.list_evidence(db, signal.id)


@router.post("/{signal_id}/evidence", response_model=MarketSignalEvidenceResponse, status_code=status.HTTP_201_CREATED)
def create_signal_evidence(signal_id: int, data: MarketSignalEvidenceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_write(db, current_user, signal.organization_id)
    return service.create_evidence(db, signal.id, data)


@router.get("/{signal_id}/evidence/{evidence_id}", response_model=MarketSignalEvidenceResponse)
def get_signal_evidence(signal_id: int, evidence_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_access(db, current_user, signal.organization_id)
    evidence = service.get_evidence(db, signal.id, evidence_id)
    if evidence is None:
        raise EvidenceNotFound("Evidence not found")
    return evidence


@router.patch("/{signal_id}/evidence/{evidence_id}", response_model=MarketSignalEvidenceResponse)
def update_signal_evidence(signal_id: int, evidence_id: int, data: MarketSignalEvidenceUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_write(db, current_user, signal.organization_id)
    evidence = service.get_evidence(db, signal.id, evidence_id)
    if evidence is None:
        raise EvidenceNotFound("Evidence not found")
    return service.update_evidence(db, evidence, data)


@router.get("/{signal_id}/assessment", response_model=MarketSignalAssessmentResponse)
def assess_market_signal(signal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_access(db, current_user, signal.organization_id)
    return service.assess(db, signal)


@router.post("/{signal_id}/requirement-candidate", response_model=RequirementCandidateResponse, status_code=status.HTTP_201_CREATED)
def create_requirement_candidate(signal_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    signal = signal_or_404(db, signal_id)
    require_organization_write(db, current_user, signal.organization_id)
    try:
        return service.create_candidate(db, signal)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


candidate_router = APIRouter(prefix="/requirement-candidates", tags=["Requirement Candidates"])


@candidate_router.get("", response_model=list[RequirementCandidateResponse])
def list_requirement_candidates(
    organization_id: int = Query(..., gt=0),
    company_id: int | None = Query(default=None, gt=0),
    candidate_status: RequirementCandidateStatus | None = Query(default=None, alias="status"),
    demand_strength: DemandStrength | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_organization_access(db, current_user, organization_id)
    return service.list_candidates(db, organization_id, company_id=company_id, status=candidate_status, demand_strength=demand_strength)


@candidate_router.get("/{candidate_id}", response_model=RequirementCandidateResponse)
def get_requirement_candidate(candidate_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    candidate = candidate_or_404(db, candidate_id)
    require_organization_access(db, current_user, candidate.organization_id)
    return candidate


@candidate_router.patch("/{candidate_id}", response_model=RequirementCandidateResponse)
def update_requirement_candidate(candidate_id: int, data: RequirementCandidateUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    candidate = candidate_or_404(db, candidate_id)
    require_organization_write(db, current_user, candidate.organization_id)
    return service.update_candidate(db, candidate, data, current_user)


@candidate_router.post("/{candidate_id}/transition", response_model=RequirementCandidateResponse)
def transition_requirement_candidate(candidate_id: int, data: RequirementCandidateTransition, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    candidate = candidate_or_404(db, candidate_id)
    require_organization_write(db, current_user, candidate.organization_id)
    return service.transition_candidate(db, candidate, data.target_status, current_user)