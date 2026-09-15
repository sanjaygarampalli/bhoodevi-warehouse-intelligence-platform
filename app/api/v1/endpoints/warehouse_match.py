from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.warehouse_match import (
    WarehouseMatchCreate,
    WarehouseMatchResponse,
    WarehouseMatchUpdate,
    WarehouseMatchRecommendationResponse,
    WarehouseMatchGenerationResponse,
)
from app.services.warehouse_match import WarehouseMatchService
from app.services.organization_access import (
    organization_for_lead,
    organization_for_match,
    organization_for_requirement,
    require_organization_access,
    require_organization_write,
)

router = APIRouter(
    prefix="/warehouse-matches",
    tags=["Warehouse Matches"],
)

match_service = WarehouseMatchService()


@router.post("/requirements/{requirement_id}/generate", response_model=WarehouseMatchGenerationResponse)
def generate_warehouse_matches(
    requirement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_organization_write(db, current_user, organization_for_requirement(db, requirement_id))
    """Generate or refresh persisted rule-based matches without replacing reviews."""
    try:
        result = match_service.generate_matches_for_requirement(db, requirement_id)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Match data changed concurrently; retry generation") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return result


@router.get("/requirements/{requirement_id}/recommendations", response_model=WarehouseMatchRecommendationResponse)
def recommend_warehouses(
    requirement_id: int,
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    organization_id = organization_for_requirement(db, requirement_id)
    if organization_id is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    require_organization_access(db, current_user, organization_id)
    """Recalculate ranked recommendations without modifying saved matches."""
    result = match_service.recommend_for_requirement(db, requirement_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return result


@router.post("/", response_model=WarehouseMatchResponse)
def create_new_warehouse_match(
    match: WarehouseMatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_organization_write(db, current_user, organization_for_lead(db, match.lead_id))
    created = match_service.create_match(db, match)
    if created is None:
        raise HTTPException(
            status_code=404,
            detail="Lead, warehouse, or requirement not found",
        )
    return created


@router.get("/", response_model=list[WarehouseMatchResponse])
def read_warehouse_matches(
    lead_id: int | None = None,
    warehouse_id: int | None = None,
    requirement_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = [
        lead_id is not None,
        warehouse_id is not None,
        requirement_id is not None,
    ]
    if sum(filters) > 1:
        raise HTTPException(
            status_code=400,
            detail="Provide only one of lead_id, warehouse_id, or requirement_id",
        )

    if lead_id is not None:
        require_organization_access(db, current_user, organization_for_lead(db, lead_id))
        return match_service.list_matches_for_lead(
            db,
            lead_id,
            limit=limit,
            offset=offset,
        )
    if warehouse_id is not None:
        from app.models.warehouse import Warehouse
        warehouse = db.get(Warehouse, warehouse_id)
        if warehouse is None:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        require_organization_access(db, current_user, warehouse.organization_id)
        return match_service.list_matches_for_warehouse(
            db,
            warehouse_id,
            limit=limit,
            offset=offset,
        )
    if requirement_id is not None:
        require_organization_access(db, current_user, organization_for_requirement(db, requirement_id))
        return match_service.list_matches_for_requirement(
            db,
            requirement_id,
            limit=limit,
            offset=offset,
        )

    raise HTTPException(
        status_code=400,
        detail="Provide one of lead_id, warehouse_id, or requirement_id",
    )


@router.get("/{match_id}", response_model=WarehouseMatchResponse)
def read_warehouse_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = match_service.get_match_by_id(db, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Warehouse match not found")
    require_organization_access(db, current_user, organization_for_match(db, match_id))
    return match


@router.put("/{match_id}", response_model=WarehouseMatchResponse)
def update_existing_warehouse_match(
    match_id: int,
    match: WarehouseMatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = match_service.get_match_by_id(db, match_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Warehouse match not found")
    require_organization_write(db, current_user, organization_for_match(db, match_id))
    updated = match_service.update_match(db, match_id, match)
    if updated is None:
        raise HTTPException(status_code=404, detail="Warehouse match not found")
    return updated


@router.delete("/{match_id}")
def delete_existing_warehouse_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = match_service.get_match_by_id(db, match_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Warehouse match not found")
    require_organization_write(db, current_user, organization_for_match(db, match_id))
    deleted = match_service.delete_match(db, match_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Warehouse match not found")
    return {"message": "Warehouse match deleted successfully"}