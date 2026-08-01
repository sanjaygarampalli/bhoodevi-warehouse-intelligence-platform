from typing import Generic, TypeVar, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, model: type[T]) -> None:
        self.model = model

    def create(self, db: Session, obj: T) -> T:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[T]:
        stmt = select(self.model).where(self.model.id == id)
        result = db.execute(stmt).scalar_one_or_none()
        return result

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        results = db.execute(stmt).scalars().all()
        return results

    def count(self, db: Session) -> int:
        stmt = select(func.count(self.model.id))
        result = db.execute(stmt).scalar()
        return result

    def exists(self, db: Session, id: int) -> bool:
        stmt = select(self.model).where(self.model.id == id)
        result = db.execute(stmt).scalar_one_or_none()
        return result is not None

    def update(self, db: Session, obj: T) -> T:
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, obj: T) -> None:
        db.delete(obj)
        db.commit()
