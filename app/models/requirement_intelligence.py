import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RequirementEvidenceClassification(str, enum.Enum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    UNKNOWN = "UNKNOWN"


class RequirementEvidenceVerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    REVIEWED = "REVIEWED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class RequirementFreshness(str, enum.Enum):
    FRESH = "FRESH"
    AGING = "AGING"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class RequirementIntelligenceEvidence(Base):
    """Requirement-specific provenance; this deliberately does not duplicate F5 claims."""

    __tablename__ = "requirement_intelligence_evidence"
    __table_args__ = (
        Index("ix_requirement_intelligence_evidence__requirement", "requirement_id"),
        Index("ix_requirement_intelligence_evidence__organization", "organization_id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    observed_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    inference: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[RequirementEvidenceClassification] = mapped_column(
        Enum(RequirementEvidenceClassification, name="requirementevidenceclassification"), nullable=False
    )
    evidence_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[RequirementEvidenceVerificationStatus] = mapped_column(
        Enum(RequirementEvidenceVerificationStatus, name="requirementevidenceverificationstatus"),
        nullable=False,
        default=RequirementEvidenceVerificationStatus.UNVERIFIED,
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verified_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    requirement = relationship("Requirement", back_populates="intelligence_evidence")
    verified_by_user = relationship("User")


class RequirementIntelligenceAssessment(Base):
    """Explainable, human-readable qualification dimensions for a requirement."""

    __tablename__ = "requirement_intelligence_assessments"
    __table_args__ = (
        Index("ix_requirement_intelligence_assessments__organization", "organization_id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, unique=True)
    requirement_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    geography_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    size_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    timing_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    operational_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    commercial_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    evidence_strength: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    freshness: Mapped[RequirementFreshness] = mapped_column(
        Enum(RequirementFreshness, name="requirementfreshness"), nullable=False, default=RequirementFreshness.UNKNOWN
    )
    freshness_anchor: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    requirement = relationship("Requirement", back_populates="intelligence_assessment")