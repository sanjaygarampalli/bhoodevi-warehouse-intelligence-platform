"""Assigned work, distinct from LeadActivity's interaction/outcome record."""
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.lead import Lead
    from app.models.user import User


class TaskType(str, Enum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"
    MEETING = "MEETING"
    PROPOSAL_FOLLOWUP = "PROPOSAL_FOLLOWUP"
    REVIEW = "REVIEW"
    ADMIN = "ADMIN"
    OTHER = "OTHER"


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


def as_utc(value: datetime) -> datetime:
    # SQLite strips offsets; all task writes normalize to UTC before storage.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"
    __table_args__ = (
        CheckConstraint("task_type IN ('CALL','EMAIL','LINKEDIN','WHATSAPP','MEETING','PROPOSAL_FOLLOWUP','REVIEW','ADMIN','OTHER')", name="ck_follow_up_tasks__type"),
        CheckConstraint("priority IN ('LOW','MEDIUM','HIGH','URGENT')", name="ck_follow_up_tasks__priority"),
        CheckConstraint("status IN ('OPEN','IN_PROGRESS','COMPLETED','CANCELLED')", name="ck_follow_up_tasks__status"),
        CheckConstraint(
            "(status = 'COMPLETED' AND completed_at IS NOT NULL AND cancelled_at IS NULL) OR "
            "(status = 'CANCELLED' AND cancelled_at IS NOT NULL AND completed_at IS NULL) OR "
            "(status IN ('OPEN','IN_PROGRESS') AND completed_at IS NULL AND cancelled_at IS NULL)",
            name="ck_follow_up_tasks__closure",
        ),
        CheckConstraint("length(trim(subject)) > 0", name="ck_follow_up_tasks__subject"),
        Index("ix_follow_up_tasks__assigned_to_user_id__status__due_at", "assigned_to_user_id", "status", "due_at"),
        Index("ix_follow_up_tasks__lead_id__status", "lead_id", "status"),
        Index("ix_follow_up_tasks__due_at", "due_at"),
        Index("ix_follow_up_tasks__deal_id", "deal_id"),
        Index("uq_follow_up_tasks__active_recommendation", "lead_id", "recommendation_key", unique=True,
              sqlite_where=text("status IN ('OPEN','IN_PROGRESS') AND recommendation_key IS NOT NULL"),
              postgresql_where=text("status IN ('OPEN','IN_PROGRESS') AND recommendation_key IS NOT NULL")),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="RESTRICT"))
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id", ondelete="RESTRICT"))
    assigned_to_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    task_type: Mapped[str] = mapped_column(String(30), default="OTHER", server_default="OTHER")
    priority: Mapped[str] = mapped_column(String(10), default="MEDIUM", server_default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), default="OPEN", server_default="OPEN")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_notes: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    recommendation_key: Mapped[str | None] = mapped_column(String(50))
    recommendation_context: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lead: Mapped["Lead"] = relationship("Lead")
    deal: Mapped["Deal | None"] = relationship("Deal")
    assigned_to_user: Mapped["User | None"] = relationship("User")

    def overdue_at(self, now: datetime) -> bool:
        return self.status in ("OPEN", "IN_PROGRESS") and as_utc(self.due_at) < as_utc(now)