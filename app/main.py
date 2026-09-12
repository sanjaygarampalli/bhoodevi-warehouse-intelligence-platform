from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.routes import router
from app.core.config import settings
from app.core.logging import logger
from app.services.deal_workflow import DealConflict, DealNotFound
from app.services.follow_up_workflow import TaskConflict, TaskNotFound
from app.services.market_signal_intelligence import (
    CandidateAlreadyExists,
    CandidateNotEligible,
    EvidenceNotFound,
    InvalidCompanyOrganization,
    InvalidStatusTransition,
    MarketSignalConflict,
    MarketSignalNotFound,
    RequirementCandidateNotFound,
)
from app.services.company_intelligence import (
    CompanyContactMethodNotFound,
    CompanyContactNotFound,
    CompanyIntelligenceNotFound,
    CompanyIntelligenceOrganizationError,
    CompanyWarehouseProfileNotFound,
    DuplicateContactMethod,
    DuplicateIntelligenceProfile,
    InvalidContactMethodValue,
)

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


@app.exception_handler(MarketSignalNotFound)
@app.exception_handler(EvidenceNotFound)
@app.exception_handler(RequirementCandidateNotFound)
async def market_signal_not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidStatusTransition)
@app.exception_handler(InvalidCompanyOrganization)
@app.exception_handler(CandidateNotEligible)
async def market_signal_bad_request_handler(request, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(MarketSignalConflict)
@app.exception_handler(CandidateAlreadyExists)
async def market_signal_conflict_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})

@app.exception_handler(CompanyIntelligenceNotFound)
@app.exception_handler(CompanyContactNotFound)
@app.exception_handler(CompanyContactMethodNotFound)
@app.exception_handler(CompanyWarehouseProfileNotFound)
async def company_intelligence_not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(CompanyIntelligenceOrganizationError)
async def company_intelligence_bad_request_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Resource not found"})

@app.exception_handler(DuplicateContactMethod)
@app.exception_handler(DuplicateIntelligenceProfile)
async def company_intelligence_conflict_handler(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidContactMethodValue)
async def company_intelligence_validation_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})