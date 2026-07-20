from fastapi import FastAPI

from app.api.v1.routes import router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Warehouse Demand Intelligence Platform",
    version=settings.APP_VERSION,
)

app.include_router(router)