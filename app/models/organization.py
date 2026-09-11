from datetime import datetime
import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Index,
    JSON,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.industry import Industry


class OrgType(str, enum.Enum):
    SOLE_PROPRIETOR = "SOLE_PROPRIETOR"
    PARTNERSHIP = "PARTNERSHIP"
    LLP = "LLP"
    PVT_LTD = "PVT_LTD"
    PUBLIC_LTD = "PUBLIC_LTD"
    GOVT = "GOVT"
    OTHER = "OTHER"


class SubscriptionTier(str, enum.Enum):
    FREE = "FREE"
    STARTER = "STARTER"
    GROWTH = "GROWTH"
    ENTERPRISE = "ENTERPRISE"


class OrganizationStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("public_id", name="uq_organizations__public_id"),
        UniqueConstraint("org_code", name="uq_organizations__org_code"),
        Index("ix_organizations__city", "city"),
        Index("ix_organizations__legal_name", "legal_name"),
        Index("ix_organizations__industry_id", "industry_id"),
        Index(
            "uq_organizations__gstin", "gstin", unique=True,
            postgresql_where=text("gstin IS NOT NULL"),
            sqlite_where=text("gstin IS NOT NULL"),
        ),
        Index(
            "uq_organizations__pan", "pan", unique=True,
            postgresql_where=text("pan IS NOT NULL"),
            sqlite_where=text("pan IS NOT NULL"),
        ),
        CheckConstraint(
            "email IS NULL OR email LIKE '%@%'",
            name="ck_organizations__email",
        ),
        CheckConstraint(
            "status IN ('TRIAL','ACTIVE','SUSPENDED','CANCELLED')",
            name="ck_organizations__status",
        ),
        CheckConstraint(
            "org_type IN ('SOLE_PROPRIETOR','PARTNERSHIP','LLP','PVT_LTD','PUBLIC_LTD','GOVT','OTHER')",
            name="ck_organizations__orgtype",
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    public_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    org_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    legal_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    trading_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    org_type: Mapped[OrgType] = mapped_column(
        Enum(OrgType, name="orgtype"),
        nullable=False,
    )

    industry_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "industries.id", name="organizations_industry_id_fkey", ondelete="SET NULL"
        ),
        nullable=True,
    )

    gstin: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
    )

    pan: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    address_line1: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    address_line2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="India",
        server_default=text("'India'"),
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscriptiontier"),
        nullable=False,
    )

    status: Mapped[OrganizationStatus] = mapped_column(
        Enum(OrganizationStatus, name="organizationstatus"),
        nullable=False,
    )

    settings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    # Relationships
    industry: Mapped["Industry | None"] = relationship("Industry")
    companies: Mapped[list["Company"]] = relationship("Company", back_populates="organization_owners")
    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership", back_populates="organization", cascade="all, delete-orphan"
    )