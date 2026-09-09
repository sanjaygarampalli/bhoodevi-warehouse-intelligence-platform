from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.routes import router
from app.core.config import settings
from app.core.logging import logger
from app.services.deal_workflow import DealConflict, DealNotFound
from app.services.follow_up_workflow import TaskConflict, TaskNotFound

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered Warehouse Demand Intelligence Platform",
    version=settings.APP_VERSION,
)

logger.info("BWIP Application Started")

app.include_router(router)


@app.exception_handler(DealConflict)
@app.exception_handler(TaskConflict)
async def deal_conflict_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(DealNotFound)
@app.exception_handler(TaskNotFound)
async def deal_not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})