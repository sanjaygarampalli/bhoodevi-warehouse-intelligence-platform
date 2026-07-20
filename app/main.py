from fastapi import FastAPI

from app.api.v1.routes import router
from app.core.config import settings
from app.core.logging import logger

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Warehouse Demand Intelligence Platform",
    version=settings.APP_VERSION,
)

logger.info("BWIP Application Started")

app.include_router(router)