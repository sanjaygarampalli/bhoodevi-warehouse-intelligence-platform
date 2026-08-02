from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse
from app.repositories.warehouse import WarehouseRepository
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


class WarehouseService:
    def __init__(self) -> None:
        self.repository = WarehouseRepository()

    def create_warehouse(
        self,
        db: Session,
        warehouse: WarehouseCreate,
    ) -> Warehouse:
        db_warehouse = Warehouse(**warehouse.model_dump())
        return self.repository.create(db, db_warehouse)

    def get_warehouse_by_id(
        self,
        db: Session,
        warehouse_id: int,
    ) -> Warehouse | None:
        return self.repository.get_by_id(db, warehouse_id)

    def list_warehouses(
        self,
        db: Session,
    ) -> list[Warehouse]:
        return self.repository.get_multi(db)

    def list_available_warehouses(
        self,
        db: Session,
    ) -> list[Warehouse]:
        return self.repository.get_available(db)

    def get_warehouses_by_city(
        self,
        db: Session,
        city: str,
    ) -> list[Warehouse]:
        return self.repository.get_by_city(db, city)

    def get_warehouses_by_state(
        self,
        db: Session,
        state: str,
    ) -> list[Warehouse]:
        return self.repository.get_by_state(db, state)

    def get_warehouses_by_owner(
        self,
        db: Session,
        owner_id: int,
    ) -> list[Warehouse]:
        return self.repository.get_by_owner(db, owner_id)

    def update_warehouse(
        self,
        db: Session,
        warehouse_id: int,
        warehouse: WarehouseUpdate,
    ) -> Warehouse | None:
        db_warehouse = self.repository.get_by_id(
            db,
            warehouse_id,
        )

        if db_warehouse is None:
            return None

        update_data = warehouse.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_warehouse, key, value)

        return self.repository.update(
            db,
            db_warehouse,
        )

    def delete_warehouse(
        self,
        db: Session,
        warehouse_id: int,
    ) -> Warehouse | None:
        db_warehouse = self.repository.get_by_id(
            db,
            warehouse_id,
        )

        if db_warehouse is None:
            return None

        self.repository.delete(
            db,
            db_warehouse,
        )

        return db_warehouse