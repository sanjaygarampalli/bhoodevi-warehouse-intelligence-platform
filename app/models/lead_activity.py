import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActivityType(str, enum.Enum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"
    MEETING = "MEETING"
    NOTE = "NOTE"
    TASK = "TASK"
    SYSTEM_EVENT = "SYSTEM_EVENT"
    AI_ACTION = "AI_ACTION"
    SIGNAL = "SIGNAL"
    PROPOSAL = "PROPOSAL"
    OTHER = "OTHER"


class ActivityChannel(str, enum.Enum):
    EMAIL = "EMAIL"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"
    PHONE = "PHONE"
    FACE_TO_FACE = "FACE_TO_FACE"
    SYSTEM = "SYSTEM"


class ActivityStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ActivityOutcome(str, enum.Enum):
    COMPLETED = "COMPLETED"
    NO_ANSWER = "NO_ANSWER"
    LEFT_VOICEMAIL = "LEFT_VOICEMAIL"
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    CALLBACK_SCHEDULED = "CALLBACK_SCHEDULED"
    BOUNCED = "BOUNCED"
    FAILED = "FAILED"
    OTHER = "OTHER"


class ActivitySourceType(str, enum.Enum):
    EMAIL = "EMAIL"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"
    TASK = "TASK"
    SYSTEM = "SYSTEM"


class LeadActivity(Base):
    __tablename__ = "lead_activities"
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"), nullable=False, index=True)

    activity_type: Mapped[ActivityType] = mapped_column(Enum(ActivityType, name="activitytype"), nullable=False, index=True)

    subject: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    activity_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    next_followup_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[ActivityStatus] = mapped_column(Enum(ActivityStatus, name="activitystatus"), nullable=False, default=ActivityStatus.SCHEDULED, index=True)

    outcome: Mapped[ActivityOutcome | None] = mapped_column(Enum(ActivityOutcome, name="activityoutcome"), nullable=True)

    performed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    channel: Mapped[ActivityChannel | None] = mapped_column(Enum(ActivityChannel, name="activitychannel"), nullable=True)

    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    activity_source_type: Mapped[ActivitySourceType | None] = mapped_column(Enum(ActivitySourceType, name="activitysourcetype"), nullable=True)

    activity_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="activities")
    performed_by_user: Mapped["User | None"] = relationship("User")