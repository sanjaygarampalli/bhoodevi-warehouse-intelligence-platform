import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MarketSignalType(str, enum.Enum):
    COMPANY_EXPANSION = "COMPANY_EXPANSION"
    MANUFACTURING_EXPANSION = "MANUFACTURING_EXPANSION"
    LOGISTICS_EXPANSION = "LOGISTICS_EXPANSION"
    DISTRIBUTION_EXPANSION = "DISTRIBUTION_EXPANSION"
    ECOMMERCE_EXPANSION = "ECOMMERCE_EXPANSION"
    NEW_FACILITY = "NEW_FACILITY"
    NEW_WAREHOUSE = "NEW_WAREHOUSE"
    NEW_DISTRIBUTION_CENTER = "NEW_DISTRIBUTION_CENTER"
    MARKET_ENTRY = "MARKET_ENTRY"
    CAPACITY_EXPANSION = "CAPACITY_EXPANSION"
    INDUSTRIAL_INVESTMENT = "INDUSTRIAL_INVESTMENT"
    LAND_ACQUISITION = "LAND_ACQUISITION"
    GOVERNMENT_TENDER = "GOVERNMENT_TENDER"
    OTHER = "OTHER"


class MarketSignalStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class MarketSignalSourceType(str, enum.Enum):
    COMPANY_ANNOUNCEMENT = "COMPANY_ANNOUNCEMENT"
    GOVERNMENT_ANNOUNCEMENT = "GOVERNMENT_ANNOUNCEMENT"
    NEWS = "NEWS"
    INDUSTRY_REPORT = "INDUSTRY_REPORT"
    TENDER_PORTAL = "TENDER_PORTAL"
    COMPANY_WEBSITE = "COMPANY_WEBSITE"
    MANUAL_RESEARCH = "MANUAL_RESEARCH"
    OTHER = "OTHER"


class MarketSignalConfidence(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EvidenceCredibility(str, enum.Enum):
    PRIMARY = "PRIMARY"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RequirementCandidateStatus(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"


class DemandStrength(str, enum.Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    POSSIBLE = "POSSIBLE"
    WEAK = "WEAK"
    NONE = "NONE"


class MarketSignal(Base):
    __tablename__ = "market_signals"
    __table_args__ = (
        Index("ix_market_signals__organization__status", "organization_id", "status"),
        Index("ix_market_signals__organization__company", "organization_id", "company_id"),
        Index("ix_market_signals__organization__type", "organization_id", "signal_type"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    signal_type: Mapped[MarketSignalType] = mapped_column(Enum(MarketSignalType, name="marketsignaltype"), nullable=False)
    status: Mapped[MarketSignalStatus] = mapped_column(Enum(MarketSignalStatus, name="marketsignalstatus"), nullable=False, default=MarketSignalStatus.DETECTED)
    source_type: Mapped[MarketSignalSourceType] = mapped_column(Enum(MarketSignalSourceType, name="marketsignalsourcetype"), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    announced_investment_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    announced_investment_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    confidence_level: Mapped[MarketSignalConfidence] = mapped_column(Enum(MarketSignalConfidence, name="marketsignalconfidence"), nullable=False, default=MarketSignalConfidence.LOW)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


class MarketSignalEvidence(Base):
    __tablename__ = "market_signal_evidence"
    __table_args__ = (
        Index("ix_market_signal_evidence__signal", "market_signal_id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_signal_id: Mapped[int] = mapped_column(ForeignKey("market_signals.id", ondelete="CASCADE"), nullable=False)
    evidence_type: Mapped[MarketSignalSourceType] = mapped_column(Enum(MarketSignalSourceType, name="evidencesourcetype"), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    credibility_level: Mapped[EvidenceCredibility] = mapped_column(Enum(EvidenceCredibility, name="evidencecredibility"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())


class RequirementCandidate(Base):
    __tablename__ = "requirement_candidates"
    __table_args__ = (
        UniqueConstraint("market_signal_id", name="uq_requirement_candidates__market_signal"),
        Index("ix_requirement_candidates__organization__status", "organization_id", "status"),
        Index("ix_requirement_candidates__organization__company", "organization_id", "company_id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    market_signal_id: Mapped[int] = mapped_column(ForeignKey("market_signals.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[RequirementCandidateStatus] = mapped_column(Enum(RequirementCandidateStatus, name="requirementcandidatestatus"), nullable=False, default=RequirementCandidateStatus.CANDIDATE)
    demand_strength: Mapped[DemandStrength] = mapped_column(Enum(DemandStrength, name="demandstrength"), nullable=False)
    confidence_level: Mapped[MarketSignalConfidence] = mapped_column(Enum(MarketSignalConfidence, name="candidateconfidence"), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, server_default=func.now())
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)