from fastapi import APIRouter

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