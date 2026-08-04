from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate


class UserService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    def get_user_by_id(
        self,
        db: Session,
        user_id: int,
    ):
        return self.repository.get_by_id(db, user_id)

    def get_user_by_email(
        self,
        db: Session,
        email: str,
    ):
        return self.repository.get_by_email(db, email)

    def list_users(
        self,
        db: Session,
    ):
        return self.repository.get_multi(db)

    def list_active_users(
        self,
        db: Session,
    ):
        return self.repository.get_active_users(db)

    def create_user(
        self,
        db: Session,
        user: UserCreate,
    ) -> User:
        db_user = User(
            full_name=user.full_name,
            email=user.email,
            hashed_password=hash_password(user.password),
            role=user.role,
            is_active=user.is_active,
        )

        return self.repository.create(
            db,
            db_user,
        )

    def update_user(
        self,
        db: Session,
        user: User,
    ):
        return self.repository.update(db, user)

    def delete_user(
        self,
        db: Session,
        user: User,
    ):
        return self.repository.delete(db, user)

    def authenticate_user(
        self,
        db: Session,
        email: str,
        password: str,
    ) -> User | None:
        user = self.get_user_by_email(db, email)

        if user is None:
            return None

        if not verify_password(
            password,
            user.hashed_password,
        ):
            return None

        return user