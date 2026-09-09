from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.lead import LeadPriority

if TYPE_CHECKING:
    from app.models.lead import Lead


class LeadScoreSnapshot(Base):
    __tablename__ = "lead_score_snapshots"
    __table_args__ = (
        CheckConstraint(
            "total_score >= 0 AND total_score <= 100",
            name="ck_lead_score_snapshots__total_score_range",
        ),
        Index("ix_lead_score_snapshots__lead_id__calculated_at", "lead_id", "calculated_at", "id"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False,
    )
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[LeadPriority] = mapped_column(
        Enum(LeadPriority, name="leadpriority"), nullable=False,
    )
    scoring_version: Mapped[str] = mapped_column(String(30), nullable=False)
    reasons: Mapped[list[dict]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False,
    )
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    lead: Mapped["Lead"] = relationship("Lead", back_populates="score_snapshots")