from app.models.user import User
from app.repositories.user import UserRepository
from app.core.security import verify_password


class UserService:
    def __init__(self) -> None:
        self.repository = UserRepository()

    def get_user_by_id(self, db, user_id: int):
        return self.repository.get_by_id(db, user_id)

    def get_user_by_email(self, db, email: str):
        return self.repository.get_by_email(db, email)

    def list_users(self, db):
        return self.repository.get_multi(db)

    def list_active_users(self, db):
        return self.repository.get_active_users(db)

    def create_user(self, db, user):
        return self.repository.create(db, user)

    def update_user(self, db, user):
        return self.repository.update(db, user)

    def delete_user(self, db, user):
        return self.repository.delete(db, user)

    def authenticate_user(self, db, email: str, password: str) -> User | None:
        user = self.get_user_by_email(db, email)
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user