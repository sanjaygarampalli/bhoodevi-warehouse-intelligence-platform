from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.deal_pipeline_stage import DealPipelineStageCreate, DealPipelineStageResponse, DealPipelineStageUpdate
from app.services.deal_pipeline_stage import DealPipelineStageService

router = APIRouter(prefix="/deal-pipeline-stages", tags=["Deal Pipeline Stages"])
stage_service = DealPipelineStageService()


@router.get("/", response_model=list[DealPipelineStageResponse])
def list_stages(
    organization_id: int | None = Query(None, gt=0),
    is_active: bool | None = None,
    skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    return stage_service.list_stages(db, organization_id=organization_id, is_active=is_active, skip=skip, limit=limit)


@router.post("/", response_model=DealPipelineStageResponse)
def create_stage(
    stage: DealPipelineStageCreate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return stage_service.create_stage(db, stage)


@router.get("/{stage_id}", response_model=DealPipelineStageResponse)
def get_stage(stage_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return stage_service.get_stage(db, stage_id)


@router.put("/{stage_id}", response_model=DealPipelineStageResponse)
def update_stage(
    stage_id: int, stage: DealPipelineStageUpdate,
    db: Session = Depends(get_db), current_user: User = Depends(get_current_admin),
):
    return stage_service.update_stage(db, stage_id, stage)


@router.delete("/{stage_id}")
def delete_stage(stage_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    stage_service.delete_stage(db, stage_id)
    return {"message": "Deal pipeline stage deleted successfully"}