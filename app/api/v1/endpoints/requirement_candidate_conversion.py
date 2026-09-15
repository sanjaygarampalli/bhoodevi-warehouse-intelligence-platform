from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.requirement_candidate_conversion import (
    RequirementCandidateConversionRequest,
    RequirementCandidateConversionResult,
)
from app.services.organization_access import require_organization_write
from app.services.requirement_candidate_conversion import (
    RequirementCandidateConversionError,
    RequirementCandidateConversionService,
)

router = APIRouter(prefix="/workflow", tags=["Workflow"])
service = RequirementCandidateConversionService()


@router.post(
    "/requirement-candidates/{candidate_id}/convert",
    response_model=RequirementCandidateConversionResult,
)
def convert_requirement_candidate(
    candidate_id: int,
    payload: RequirementCandidateConversionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.market_signal import RequirementCandidate

    candidate = db.get(RequirementCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requirement candidate not found")
    require_organization_write(db, current_user, candidate.organization_id)
    try:
        conversion, company, lead, requirement, created = service.convert(
            db, candidate_id, payload, user_id=current_user.id, organization_id=candidate.organization_id,
        )
        return RequirementCandidateConversionResult(
            conversion=conversion, company=company, lead=lead, requirement=requirement, created=created,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RequirementCandidateConversionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc