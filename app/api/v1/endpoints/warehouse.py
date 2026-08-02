from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.services.warehouse import WarehouseService

router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
)

warehouse_service = WarehouseService()


@router.post("/", response_model=WarehouseResponse)
def create_new_warehouse(
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    return warehouse_service.create_warehouse(db, warehouse)


@router.get("/", response_model=list[WarehouseResponse])
def read_all_warehouses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return warehouse_service.list_warehouses(db)


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def read_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    warehouse = warehouse_service.get_warehouse_by_id(
        db,
        warehouse_id,
    )

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found",
        )

    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_existing_warehouse(
    warehouse_id: int,
    warehouse: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = warehouse_service.update_warehouse(
        db,
        warehouse_id,
        warehouse,
    )

    if updated is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found",
        )

    return updated


@router.delete("/{warehouse_id}")
def delete_existing_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = warehouse_service.delete_warehouse(
        db,
        warehouse_id,
    )

    if deleted is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found",
        )

    return {
        "message": "Warehouse deleted successfully"
    }