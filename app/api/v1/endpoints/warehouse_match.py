from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.warehouse_match import (
    WarehouseMatchCreate,
    WarehouseMatchResponse,
    WarehouseMatchUpdate,
)
from app.services.warehouse_match import WarehouseMatchService

router = APIRouter(
    prefix="/warehouse-matches",
    tags=["Warehouse Matches"],
)

match_service = WarehouseMatchService()


@router.post("/", response_model=WarehouseMatchResponse)
def create_new_warehouse_match(
    match: WarehouseMatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
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
        return match_service.list_matches_for_lead(
            db,
            lead_id,
            limit=limit,
            offset=offset,
        )
    if warehouse_id is not None:
        return match_service.list_matches_for_warehouse(
            db,
            warehouse_id,
            limit=limit,
            offset=offset,
        )
    if requirement_id is not None:
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
    return match


@router.put("/{match_id}", response_model=WarehouseMatchResponse)
def update_existing_warehouse_match(
    match_id: int,
    match: WarehouseMatchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = match_service.update_match(db, match_id, match)
    if updated is None:
        raise HTTPException(status_code=404, detail="Warehouse match not found")
    return updated


@router.delete("/{match_id}")
def delete_existing_warehouse_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = match_service.delete_match(db, match_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Warehouse match not found")
    return {"message": "Warehouse match deleted successfully"}