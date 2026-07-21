from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import (
    create_warehouse,
    delete_warehouse,
    get_warehouse,
    get_warehouses,
    update_warehouse,
)
from app.db.session import get_db
from app.dependencies import get_current_user
from app.dependencies_admin import get_current_admin
from app.models.user import User
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)

router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
)


# ==========================
# Create Warehouse (Admin Only)
# ==========================
@router.post("/", response_model=WarehouseResponse)
def create_new_warehouse(
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    return create_warehouse(db, warehouse)


# ==========================
# Get All Warehouses (Any Logged-in User)
# ==========================
@router.get("/", response_model=list[WarehouseResponse])
def read_all_warehouses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_warehouses(db)


# ==========================
# Get Warehouse by ID (Any Logged-in User)
# ==========================
@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def read_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    warehouse = get_warehouse(db, warehouse_id)

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found",
        )

    return warehouse


# ==========================
# Update Warehouse (Admin Only)
# ==========================
@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_existing_warehouse(
    warehouse_id: int,
    warehouse: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    updated = update_warehouse(
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


# ==========================
# Delete Warehouse (Admin Only)
# ==========================
@router.delete("/{warehouse_id}")
def delete_existing_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    deleted = delete_warehouse(
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