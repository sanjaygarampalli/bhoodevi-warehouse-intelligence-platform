from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self) -> None:
        super().__init__(model=User)

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        stmt = select(self.model).where(self.model.email == email)
        result = db.execute(stmt).scalar_one_or_none()
        return result

    def get_active_users(self, db: Session) -> List[User]:
        stmt = select(self.model).where(self.model.is_active.is_(True))
        results = db.execute(stmt).scalars().all()
        return results
