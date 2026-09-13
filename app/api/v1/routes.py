from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.follow_up_task import router as follow_up_task_router
from app.api.v1.endpoints.deal import router as deal_router
from app.api.v1.endpoints.deal_pipeline_stage import router as deal_pipeline_stage_router
from app.api.v1.endpoints.company import router as company_router
from app.api.v1.endpoints.decision_maker import router as decision_maker_router
from app.api.v1.endpoints.industry import router as industry_router
from app.api.v1.endpoints.organization import router as organization_router
from app.api.v1.endpoints.lead import router as lead_router
from app.api.v1.endpoints.lead_activity import router as lead_activity_router
from app.api.v1.endpoints.requirement import router as requirement_router
from app.api.v1.endpoints.warehouse import router as warehouse_router
from app.api.v1.endpoints.warehouse_match import router as warehouse_match_router
from app.api.v1.endpoints.workflow import router as workflow_router
from app.api.v1.endpoints.prospect_prioritization import router as prospect_prioritization_router
from app.api.v1.endpoints.operational_dashboard import router as operational_dashboard_router
from app.api.v1.endpoints.action_intelligence import router as action_intelligence_router
from app.api.v1.endpoints.organization_membership import router as organization_membership_router
from app.api.v1.endpoints.market_signal import candidate_router as requirement_candidate_router
from app.api.v1.endpoints.market_signal import router as market_signal_router
from app.api.v1.endpoints.company_intelligence import router as company_intelligence_router
from app.api.v1.endpoints.warehouse_capability import router as warehouse_capability_router
from app.api.v1.endpoints.warehouse_pilot import router as warehouse_pilot_router
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
router.include_router(industry_router)
router.include_router(organization_router)
router.include_router(decision_maker_router)
router.include_router(lead_router)
router.include_router(lead_activity_router)
router.include_router(requirement_router)
router.include_router(warehouse_match_router)
router.include_router(deal_pipeline_stage_router)
router.include_router(deal_router)
router.include_router(follow_up_task_router)
router.include_router(workflow_router)
router.include_router(prospect_prioritization_router)
router.include_router(operational_dashboard_router)
router.include_router(action_intelligence_router)
router.include_router(organization_membership_router)
router.include_router(market_signal_router)
router.include_router(requirement_candidate_router)
router.include_router(company_intelligence_router)
router.include_router(warehouse_capability_router)
router.include_router(warehouse_pilot_router)
