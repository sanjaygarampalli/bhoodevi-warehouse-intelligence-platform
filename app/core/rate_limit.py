"""Atomic database-backed quotas shared by all application instances."""
import hashlib
import hmac
from time import time
from threading import Lock
from time import monotonic

from fastapi import Depends, HTTPException, Request
from sqlalchemy import case, delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.core.config import settings
from app.db.session import get_db
from app.models.rate_limit import RateLimitBucket


class FixedWindowLimiter:
    def __init__(self, limit, window_seconds, *, capacity=10000, clock=monotonic):
        self.limit, self.window_seconds, self.capacity = limit, window_seconds, capacity
        self.clock = clock
        self.entries = {}
        self.lock = Lock()

    def allow(self, key):
        with self.lock:
            now = self.clock()
            for existing, (start, _) in list(self.entries.items()):
                if now - start >= self.window_seconds:
                    del self.entries[existing]
            start, count = self.entries.get(key, (now, 0))
            if count >= self.limit or (key not in self.entries and len(self.entries) >= self.capacity):
                return False
            self.entries[key] = (start, count + 1)
            return True


class DatabaseLimiter:
    def allow(self, bind, key, limit, window_seconds):
        # Independent transaction: quota must survive rejected login/rollback,
        # and must never commit the caller's commercial transaction.
        with Session(bind) as quota:
            now = (int(quota.scalar(text("SELECT EXTRACT(EPOCH FROM clock_timestamp())")))
                   if bind.dialect.name == "postgresql" else int(time()))
            quota.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at <= now))
            insert = pg_insert if bind.dialect.name == "postgresql" else sqlite_insert
            expired = RateLimitBucket.expires_at <= now
            statement = insert(RateLimitBucket).values(key=key, count=1, expires_at=now + window_seconds)
            statement = statement.on_conflict_do_update(
                index_elements=[RateLimitBucket.key],
                set_={"count": case((expired, 1), else_=RateLimitBucket.count + 1),
                      "expires_at": case((expired, now + window_seconds), else_=RateLimitBucket.expires_at)},
                where=expired | (RateLimitBucket.count < limit),
            ).returning(RateLimitBucket.count)
            allowed = quota.scalar(statement) is not None
            quota.commit()
            return allowed


database_limiter = DatabaseLimiter()
# Injection point for isolated unit tests; production always uses the database.
auth_limiter = None


def consume_quota(db, namespace, identity, limit, window_seconds):
    key = hmac.new(settings.SECRET_KEY.encode(), f"{namespace}:{identity}".encode(), hashlib.sha256).hexdigest()
    try:
        allowed = database_limiter.allow(db.get_bind(), key, limit, window_seconds)
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Request quota service unavailable; retry later",
                            headers={"Retry-After": "5"}) from None
    if not allowed:
        raise HTTPException(status_code=429, detail="Request quota exceeded; retry later",
                            headers={"Retry-After": str(window_seconds)})


def require_auth_rate_limit(request: Request, db: Session = Depends(get_db)):
    # Do not trust arbitrary X-Forwarded-For headers. Configure trusted proxies
    # in the server/ingress when deriving client addresses behind a proxy.
    key = request.client.host if request.client else "unknown"
    if auth_limiter is None:
        consume_quota(db, "authentication", key, settings.AUTH_RATE_LIMIT, settings.AUTH_RATE_WINDOW_SECONDS)
    elif not auth_limiter.allow(key):
        raise HTTPException(status_code=429, detail="Too many authentication attempts; retry later",
                            headers={"Retry-After": str(settings.AUTH_RATE_WINDOW_SECONDS)})


def limit_expensive_operation(db, user):
    # Account-level quota cannot be bypassed by switching tenants; distinct
    # users (including users in the same tenant) have independent counters.
    consume_quota(db, "expensive", str(user.id), settings.EXPENSIVE_RATE_LIMIT, settings.EXPENSIVE_RATE_WINDOW_SECONDS)
