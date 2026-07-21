from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


def create_warehouse(db: Session, warehouse: WarehouseCreate) -> Warehouse:
    db_warehouse = Warehouse(**warehouse.model_dump())

    db.add(db_warehouse)
    db.commit()
    db.refresh(db_warehouse)

    return db_warehouse


def get_warehouses(db: Session):
    return db.query(Warehouse).all()


def get_warehouse(db: Session, warehouse_id: int):
    return db.query(Warehouse).filter(
        Warehouse.id == warehouse_id
    ).first()


def update_warehouse(
    db: Session,
    warehouse_id: int,
    warehouse: WarehouseUpdate,
):
    db_warehouse = get_warehouse(db, warehouse_id)

    if not db_warehouse:
        return None

    update_data = warehouse.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_warehouse, key, value)

    db.commit()
    db.refresh(db_warehouse)

    return db_warehouse


def delete_warehouse(
    db: Session,
    warehouse_id: int,
):
    db_warehouse = get_warehouse(db, warehouse_id)

    if not db_warehouse:
        return None

    db.delete(db_warehouse)
    db.commit()

    return db_warehouse