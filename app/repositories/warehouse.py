from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse
from app.repositories.base import BaseRepository


class WarehouseRepository(BaseRepository[Warehouse]):
    def __init__(self) -> None:
        super().__init__(model=Warehouse)

    def get_by_city(self, db: Session, city: str) -> List[Warehouse]:
        stmt = select(self.model).where(self.model.city == city)
        results = db.execute(stmt).scalars().all()
        return results

    def get_by_state(self, db: Session, state: str) -> List[Warehouse]:
        stmt = select(self.model).where(self.model.state == state)
        results = db.execute(stmt).scalars().all()
        return results

    def get_available(self, db: Session) -> List[Warehouse]:
    stmt = select(self.model).where(self.model.is_available.is_(True))
    results = db.execute(stmt).scalars().all()
    return results

    def get_by_owner(self, db: Session, owner_id: int) -> List[Warehouse]:
        stmt = select(self.model).where(self.model.owner_id == owner_id)
        results = db.execute(stmt).scalars().all()
        return results
