from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.commercial_outcome_intelligence import OutcomeSummary
from app.services.commercial_outcome_intelligence import CommercialOutcomeIntelligenceService
from app.services.organization_access import require_organization_access

router = APIRouter(prefix="/commercial-intelligence/outcomes", tags=["Commercial Intelligence"])
service = CommercialOutcomeIntelligenceService()


@router.get("/summary", response_model=OutcomeSummary)
def outcome_summary(
    organization_id: int = Query(..., gt=0),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_organization_access(db, current_user, organization_id)
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date must be on or before to_date")
    return service.summary(db, organization_id, from_date=from_date, to_date=to_date)