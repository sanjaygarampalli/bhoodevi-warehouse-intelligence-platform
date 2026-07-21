from fastapi import Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models.user import User


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return current_user