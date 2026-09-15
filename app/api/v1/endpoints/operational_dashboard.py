"""Authenticated operational intelligence dashboard endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.organization_access import require_organization_access
from app.schemas.operational_dashboard import OperationalDashboard
from app.services.operational_dashboard import OperationalDashboardService

router = APIRouter(tags=["Operational Intelligence"])
dashboard_service = OperationalDashboardService()

@router.get("/operational-dashboard", response_model=OperationalDashboard)
def read_operational_dashboard(top_priorities_limit: int = Query(5, ge=1, le=50), recent_activity_limit: int = Query(10, ge=1, le=100), organization_id: int | None = Query(None, ge=1), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if organization_id is None and current_user.role != "admin":
        raise HTTPException(status_code=400, detail="organization_id is required")
    if organization_id is not None:
        require_organization_access(db, current_user, organization_id)
    return dashboard_service.get_dashboard(db, top_priorities_limit=top_priorities_limit, recent_activity_limit=recent_activity_limit, organization_id=organization_id)
