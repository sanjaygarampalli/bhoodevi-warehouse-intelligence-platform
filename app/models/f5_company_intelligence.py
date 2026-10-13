import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class F5Classification(str, enum.Enum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    UNKNOWN = "UNKNOWN"


class F5Freshness(str, enum.Enum):
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class F5LifecycleStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    IDENTIFIED = "IDENTIFIED"
    ENRICHED = "ENRICHED"
    REGIONALLY_RELEVANT = "REGIONALLY_RELEVANT"
    ICP_EVALUATED = "ICP_EVALUATED"
    QUALIFIED_FOR_REQUIREMENT_RESEARCH = "QUALIFIED_FOR_REQUIREMENT_RESEARCH"
    DISQUALIFIED = "DISQUALIFIED"
    DUPLICATE = "DUPLICATE"
    ARCHIVED = "ARCHIVED"


class F5PresenceType(str, enum.Enum):
    OFFICE = "OFFICE"
    FACTORY = "FACTORY"
    WAREHOUSE = "WAREHOUSE"
    DISTRIBUTION_CENTER = "DISTRIBUTION_CENTER"
    RETAIL_NETWORK = "RETAIL_NETWORK"
    DEALER_NETWORK = "DEALER_NETWORK"
    PROJECT = "PROJECT"
    EXPANSION = "EXPANSION"
    LOGISTICS_ACTIVITY = "LOGISTICS_ACTIVITY"
    OTHER = "OTHER"


class F5WarehouseSuitability(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class F5DuplicateStatus(str, enum.Enum):
    NONE = "NONE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
    UNRELATED = "UNRELATED"


def _enum(enum_class: type[enum.Enum], name: str):
    return Enum(enum_class, name=name, values_callable=lambda values: [value.value for value in values])


def _json():
    return JSON().with_variant(JSONB(), "postgresql")


class F5CompanyProfile(Base):
    __tablename__ = "f5_company_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "company_id", name="uq_f5_company_profiles_org_company"),
        Index("ix_f5_company_profiles_org_status", "organization_id", "lifecycle_status"),
        Index("ix_f5_company_profiles_org_normalized_name", "organization_id", "normalized_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_domain: Mapped[str | None] = mapped_column(String(255))
    registration_identifier: Mapped[str | None] = mapped_column(String(150))
    source_identifier: Mapped[str | None] = mapped_column(String(255))
    aliases: Mapped[list[str]] = mapped_column(_json(), nullable=False, default=list)
    lifecycle_status: Mapped[F5LifecycleStatus] = mapped_column(_enum(F5LifecycleStatus, "f5lifecyclestatus"), nullable=False, default=F5LifecycleStatus.DISCOVERED)
    duplicate_status: Mapped[F5DuplicateStatus] = mapped_column(_enum(F5DuplicateStatus, "f5duplicatestatus"), nullable=False, default=F5DuplicateStatus.NONE)
    source: Mapped[str | None] = mapped_column(String(255))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    presence: Mapped[list["F5RegionalPresence"]] = relationship(cascade="all, delete-orphan")
    claims: Mapped[list["F5EvidenceClaim"]] = relationship(cascade="all, delete-orphan")


class F5RegionalPresence(Base):
    __tablename__ = "f5_regional_presence"
    __table_args__ = (Index("ix_f5_presence_profile_region", "profile_id", "region"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("f5_company_profiles.id", ondelete="CASCADE"), nullable=False)
    presence_type: Mapped[F5PresenceType] = mapped_column(_enum(F5PresenceType, "f5presencetype"), nullable=False)
    region: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100), default="India")
    classification: Mapped[F5Classification] = mapped_column(_enum(F5Classification, "f5classification"), nullable=False)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    freshness: Mapped[F5Freshness] = mapped_column(_enum(F5Freshness, "f5freshness"), nullable=False, default=F5Freshness.UNKNOWN)
    source: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    notes: Mapped[str | None] = mapped_column(Text)


class F5EvidenceClaim(Base):
    __tablename__ = "f5_evidence_claims"
    __table_args__ = (Index("ix_f5_claims_profile_type", "profile_id", "claim_type"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("f5_company_profiles.id", ondelete="CASCADE"), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(100), nullable=False)
    classification: Mapped[F5Classification] = mapped_column(_enum(F5Classification, "f5claimclassification"), nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_title: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    freshness: Mapped[F5Freshness] = mapped_column(_enum(F5Freshness, "f5claimfreshness"), nullable=False, default=F5Freshness.UNKNOWN)
    credibility: Mapped[str | None] = mapped_column(String(30))
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    confidence_reasons: Mapped[list[str]] = mapped_column(_json(), nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class F5Assessment(Base):
    __tablename__ = "f5_assessments"
    __table_args__ = (
        UniqueConstraint("organization_id", "company_id", name="uq_f5_assessments_org_company"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_f5_assessment_confidence"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    industry_classification: Mapped[F5Classification] = mapped_column(_enum(F5Classification, "f5industryclassification"), nullable=False, default=F5Classification.UNKNOWN)
    industry: Mapped[str | None] = mapped_column(String(150))
    warehouse_suitability: Mapped[F5WarehouseSuitability] = mapped_column(_enum(F5WarehouseSuitability, "f5warehousesuitability"), nullable=False, default=F5WarehouseSuitability.UNKNOWN)
    icp_classification: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    dimensions: Mapped[dict[str, Any]] = mapped_column(_json(), nullable=False, default=dict)
    reasons: Mapped[list[str]] = mapped_column(_json(), nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    confidence_reasons: Mapped[list[str]] = mapped_column(_json(), nullable=False, default=list)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    freshness: Mapped[F5Freshness] = mapped_column(_enum(F5Freshness, "f5assessmentfreshness"), nullable=False, default=F5Freshness.UNKNOWN)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)