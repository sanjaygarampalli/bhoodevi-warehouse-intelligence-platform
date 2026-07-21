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
from app.schemas.warehouse import (
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)

router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
)


@router.post("/", response_model=WarehouseResponse)
def create_new_warehouse(
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db),
):
    return create_warehouse(db, warehouse)


@router.get("/", response_model=list[WarehouseResponse])
def read_all_warehouses(
    db: Session = Depends(get_db),
):
    return get_warehouses(db)


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def read_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
):
    warehouse = get_warehouse(db, warehouse_id)

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


@router.delete("/{warehouse_id}")
def delete_existing_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
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