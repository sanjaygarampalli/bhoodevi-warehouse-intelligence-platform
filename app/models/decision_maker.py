import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DecisionLevel(str, enum.Enum):
    C_SUITE = "C_SUITE"
    VP = "VP"
    DIRECTOR = "DIRECTOR"
    MANAGER = "MANAGER"
    EXECUTIVE = "EXECUTIVE"
    OTHER = "OTHER"


class PreferredContact(str, enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"


class DecisionMakerStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    RESPONDED = "RESPONDED"
    QUALIFIED = "QUALIFIED"
    CONVERTED = "CONVERTED"
    DISQUALIFIED = "DISQUALIFIED"


class DecisionMaker(Base):
    __tablename__ = "decision_makers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    designation: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    decision_level: Mapped[DecisionLevel] = mapped_column(
        Enum(DecisionLevel, name="decisionlevel"),
        nullable=False,
        default=DecisionLevel.OTHER,
    )

    preferred_contact: Mapped[PreferredContact | None] = mapped_column(
        Enum(PreferredContact, name="preferredcontact"),
        nullable=True,
    )

    decision_maker_status: Mapped[DecisionMakerStatus] = mapped_column(
        Enum(DecisionMakerStatus, name="decisionmakerstatus"),
        nullable=False,
        default=DecisionMakerStatus.NEW,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    linkedin_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_primary_contact: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    company: Mapped["Company"] = relationship(
        "Company", back_populates="decision_makers"
    )