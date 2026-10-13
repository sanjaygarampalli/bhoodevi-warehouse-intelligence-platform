from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)
from app.db.session import get_db
from app.schemas.user import (
    Token,
    UserCreate,
    UserResponse,
    AuthenticatedContextResponse,
)
from app.dependencies import get_current_user
from app.models.organization_membership import MembershipStatus, OrganizationMembership
from app.models.user import User
from app.dependencies_admin import get_current_admin
from app.schemas.user import PasswordChange, SessionRevocation
from app.core.security import hash_password, verify_password
from app.services.user import UserService
from app.core.rate_limit import require_auth_rate_limit
from app.core.config import settings
from app.schemas.user import GoogleLogin
from app.services.google_auth import google_login, issue_challenge

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


def require_google_origin(request: Request):
    # JSON callback flow, no cookies or redirect endpoint. Only configured frontend origins.
    if request.headers.get("origin") not in settings.CORS_ORIGINS:
        raise HTTPException(403, "Sign-in origin is not permitted")


@router.get("/google/config")
def google_config(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return {"client_id": settings.GOOGLE_CLIENT_ID or None}


@router.post("/google/challenge", dependencies=[Depends(require_auth_rate_limit), Depends(require_google_origin)])
def google_challenge(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return issue_challenge(db)


@router.post("/google", response_model=Token, dependencies=[Depends(require_auth_rate_limit), Depends(require_google_origin)])
def sign_in_google(payload: GoogleLogin, response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return google_login(db, payload.credential, payload.nonce, payload.link_password)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_auth_rate_limit)],
)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    user_service = UserService()

    existing_user = user_service.get_user_by_email(
        db,
        user.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    try:
        return user_service.create_user(
            db,
            # Public registration must not grant client-selected privileges.
            user.model_copy(update={"role": "user"}),
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered") from exc


@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(require_auth_rate_limit)],
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user_service = UserService()

    user = user_service.authenticate_user(
        db,
        form_data.username,
        form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        data={"sub": user.email, "ver": user.token_version},
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        ),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def revoke_credentials(db: Session, user_id: int, *, deactivate=False):
    values = {"token_version": User.token_version + 1}
    if deactivate:
        values["is_active"] = False
    db.execute(update(User).where(User.id == user_id).values(**values))
    db.commit()


@router.post("/logout")
def logout(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Small compatible policy: logout revokes every token for this account.
    revoke_credentials(db, current_user.id)
    return {"detail": "All account sessions revoked"}


@router.post("/change-password", dependencies=[Depends(require_auth_rate_limit)])
def change_password(payload: PasswordChange, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.scalar(select(User).where(User.id == current_user.id).with_for_update().execution_options(populate_existing=True))
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    db.execute(update(User).where(User.id == user.id).values(
        hashed_password=hash_password(payload.password), token_version=User.token_version + 1))
    db.commit()
    return {"detail": "Password changed; all account sessions revoked"}


@router.post("/users/{user_id}/revoke")
def revoke_user_sessions(user_id: int, payload: SessionRevocation, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    revoke_credentials(db, user_id, deactivate=payload.deactivate)
    return {"detail": "Account credentials revoked"}


@router.get("/me", response_model=AuthenticatedContextResponse)
def authenticated_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    memberships = db.scalars(
        select(OrganizationMembership)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(OrganizationMembership.organization_id)
    ).all()

    return {
        "user": current_user,
        "organizations": [
            {
                "organization_id": membership.organization_id,
                "public_id": membership.organization.public_id,
                "org_code": membership.organization.org_code,
                "legal_name": membership.organization.legal_name,
                "trading_name": membership.organization.trading_name,
                "role": membership.role,
                "status": membership.status,
            }
            for membership in memberships
        ],
    }
