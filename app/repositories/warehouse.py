from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse
from app.repositories.base import BaseRepository


class WarehouseRepository(BaseRepository[Warehouse]):
    def __init__(self) -> None:
        super().__init__(model=Warehouse)

    def get_by_city(
        self,
        db: Session,
        city: str,
    ) -> List[Warehouse]:
        stmt = select(self.model).where(self.model.city == city)
        return db.execute(stmt).scalars().all()

    def get_by_state(
        self,
        db: Session,
        state: str,
    ) -> List[Warehouse]:
        stmt = select(self.model).where(self.model.state == state)
        return db.execute(stmt).scalars().all()

    def get_available(
        self,
        db: Session,
    ) -> List[Warehouse]:
        # Currently all warehouses are considered available.
        # This can later be updated when an is_available column is added.
        stmt = select(self.model)
        return db.execute(stmt).scalars().all()

    def get_by_owner(
        self,
        db: Session,
        owner_id: int,
    ) -> List[Warehouse]:
        stmt = select(self.model).where(self.model.owner_id == owner_id)
        return db.execute(stmt).scalars().all()