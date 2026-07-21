from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.warehouse import router as warehouse_router
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