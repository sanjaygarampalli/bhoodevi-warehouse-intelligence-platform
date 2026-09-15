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
from app.services.organization_access import require_organization_access, require_organization_write

router = APIRouter(
    prefix="/warehouses",
    tags=["Warehouses"],
)

warehouse_service = WarehouseService()


@router.post("/", response_model=WarehouseResponse)
def create_new_warehouse(
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if warehouse.organization_id is None:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Organization ownership is required")
    else:
        require_organization_write(db, current_user, warehouse.organization_id)
    return warehouse_service.create_warehouse(db, warehouse)


@router.get("/", response_model=list[WarehouseResponse])
def read_all_warehouses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "admin":
        return warehouse_service.list_warehouses(db)
    from sqlalchemy import select
    from app.models.warehouse import Warehouse
    from app.models.organization_membership import OrganizationMembership, MembershipStatus
    return list(db.scalars(select(Warehouse).join(OrganizationMembership, OrganizationMembership.organization_id == Warehouse.organization_id).where(
        OrganizationMembership.user_id == current_user.id,
        OrganizationMembership.status == MembershipStatus.ACTIVE,
    )))


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

    require_organization_access(db, current_user, warehouse.organization_id)

    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_existing_warehouse(
    warehouse_id: int,
    warehouse: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = warehouse_service.get_warehouse_by_id(db, warehouse_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    require_organization_write(db, current_user, existing.organization_id)
    if warehouse.organization_id is not None and warehouse.organization_id != existing.organization_id:
        raise HTTPException(status_code=403, detail="Warehouse organization cannot be changed")
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
    current_user: User = Depends(get_current_user),
):
    existing = warehouse_service.get_warehouse_by_id(db, warehouse_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    require_organization_write(db, current_user, existing.organization_id)
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