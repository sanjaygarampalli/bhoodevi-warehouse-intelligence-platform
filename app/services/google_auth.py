"""Google authenticates identity; existing BWIP roles and memberships authorize data."""
import hashlib
import secrets
import time

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.models.google_login_challenge import GoogleLoginChallenge
from app.models.user import User


def require_enabled():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, "Google sign-in is not configured. Use your BWIP password.")


def issue_challenge(db: Session):
    require_enabled()
    now = int(time.time())
    nonce = secrets.token_urlsafe(32)
    db.execute(delete(GoogleLoginChallenge).where(GoogleLoginChallenge.expires_at <= now))
    db.add(GoogleLoginChallenge(nonce_hash=hashlib.sha256(nonce.encode()).hexdigest(), expires_at=now + 300))
    db.commit()
    return {"nonce": nonce, "expires_in": 300}


def verify_google_credential(credential: str) -> dict:
    # Keep the existing password login usable before this optional dependency is installed.
    try:
        from google.auth.exceptions import GoogleAuthError, TransportError
        from google.auth.transport.requests import Request
        from google.oauth2.id_token import verify_oauth2_token
    except ImportError as exc:
        raise HTTPException(503, "Google sign-in is unavailable. Use your BWIP password.") from exc

    class BoundedRequest(Request):
        def __call__(self, *args, **kwargs):
            kwargs["timeout"] = 5
            return super().__call__(*args, **kwargs)

    try:
        claims = verify_oauth2_token(credential, BoundedRequest(), settings.GOOGLE_CLIENT_ID)
    except TransportError as exc:
        raise HTTPException(503, "Google verification is temporarily unavailable. Try again.") from exc
    except (ValueError, GoogleAuthError) as exc:
        raise HTTPException(401, "Google credential is invalid or expired.") from exc
    return claims


def google_login(db: Session, credential: str, nonce: str, link_password: str | None):
    require_enabled()
    claims = verify_google_credential(credential)
    # These explicit requirements complement the library signature/issuer/audience/expiry checks.
    subject, email = claims.get("sub"), claims.get("email")
    if (not isinstance(subject, str) or not 1 <= len(subject) <= 255
            or not isinstance(email, str) or not 1 <= len(email) <= 255
            or claims.get("email_verified") is not True
            or not isinstance(claims.get("nonce"), str)
            or not secrets.compare_digest(claims["nonce"].encode(), nonce.encode())):
        raise HTTPException(401, "Google credential is invalid or unverified.")
    used = db.execute(delete(GoogleLoginChallenge).where(
        GoogleLoginChallenge.nonce_hash == hashlib.sha256(nonce.encode()).hexdigest(),
        GoogleLoginChallenge.expires_at > int(time.time()),
    ).returning(GoogleLoginChallenge.nonce_hash)).scalar_one_or_none()
    db.commit()  # Consume even failed account-link attempts; one winner across workers.
    if used is None:
        raise HTTPException(401, "Google sign-in expired or was already used. Choose Google again.")

    user = db.scalar(select(User).where(User.google_subject == subject).with_for_update())
    if user is None:
        # Never merge accounts just because an email matches, even if Google verified it.
        matches = db.scalars(select(User).where(func.lower(User.email) == email.lower()).with_for_update()).all()
        if len(matches) != 1 or not matches[0].is_active:
            raise HTTPException(403, "An active BWIP account is required. Contact your administrator.")
        user = matches[0]
        if user.google_subject is not None:
            raise HTTPException(403, "This BWIP account is connected to another Google identity.")
        if not link_password or not verify_password(link_password, user.hashed_password):
            raise HTTPException(409, "To connect Google, enter your existing BWIP password, then choose Google again.")
        user.google_subject = subject
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "Google identity was connected concurrently. Try signing in again.") from exc
    if not user.is_active:
        raise HTTPException(403, "This BWIP account is inactive. Contact your administrator.")
    token = create_access_token({"sub": user.email, "ver": user.token_version})
    db.commit()
    return {"access_token": token, "token_type": "bearer"}
