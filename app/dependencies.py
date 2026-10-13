from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    decode_access_token,
    oauth2_scheme,
)
from app.db.session import get_db
from app.models.user import User
from app.services.user import UserService


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    email = payload.get("sub")

    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_service = UserService()
    user = user_service.get_user_by_email(db, email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )

    # Version zero accepts pre-migration credentials only until first revocation.
    version = payload.get("ver", 0)
    if type(version) is not int or version != user.token_version:
        raise HTTPException(status_code=401, detail="Session has been revoked")

    return user
