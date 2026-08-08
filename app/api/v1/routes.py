from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.company import router as company_router
from app.api.v1.endpoints.decision_maker import router as decision_maker_router
from app.api.v1.endpoints.lead import router as lead_router
from app.api.v1.endpoints.lead_activity import router as lead_activity_router
from app.api.v1.endpoints.requirement import router as requirement_router
from app.api.v1.endpoints.warehouse import router as warehouse_router
from app.api.v1.endpoints.warehouse_match import router as warehouse_match_router
from app.core.config import settings

router = APIRouter()


@router.get("/")
def root():
    return {
        "application": "BWIP",
        "message": "Welcome to BHOODEVI Warehouse Intelligence Platform",
        "status": "Running",
        "version": settings.APP_VERSION,
    }


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "BWIP",
    }


router.include_router(auth_router)
router.include_router(warehouse_router)
router.include_router(company_router)
router.include_router(decision_maker_router)
router.include_router(lead_router)
router.include_router(lead_activity_router)
router.include_router(requirement_router)
router.include_router(warehouse_match_router)
