import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RequirementCandidateConversionStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONVERTED = "CONVERTED"
    FAILED = "FAILED"


class RequirementCandidateConversion(Base):
    __tablename__ = "requirement_candidate_conversions"
    __table_args__ = (
        CheckConstraint(
            "status <> 'CONVERTED' OR (company_id IS NOT NULL AND lead_id IS NOT NULL AND requirement_id IS NOT NULL)",
            name="ck_rcc__converted_records_complete",
        ),
        UniqueConstraint("requirement_candidate_id", name="uq_rcc__requirement_candidate"),
        UniqueConstraint("lead_id", name="uq_rcc__lead"),
        UniqueConstraint("requirement_id", name="uq_rcc__requirement"),
        Index("ix_rcc__organization__status", "organization_id", "status"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    requirement_candidate_id: Mapped[int] = mapped_column(ForeignKey("requirement_candidates.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id", ondelete="RESTRICT"), nullable=True)
    requirement_id: Mapped[int | None] = mapped_column(ForeignKey("requirements.id", ondelete="RESTRICT"), nullable=True)
    status: Mapped[RequirementCandidateConversionStatus] = mapped_column(
        Enum(RequirementCandidateConversionStatus, name="requirementcandidateconversionstatus"), nullable=False,
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization")
    requirement_candidate = relationship("RequirementCandidate")
    company = relationship("Company")
    lead = relationship("Lead")
    requirement = relationship("Requirement")
    created_by_user = relationship("User")