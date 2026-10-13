"""Shared fixed-window counters; keys contain HMAC digests, never raw IPs."""
from sqlalchemy import BigInteger, Integer, String, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    __table_args__ = (Index("ix_rate_limit_buckets_expires_at", "expires_at"),)
