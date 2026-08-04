from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    industry: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    company_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    products: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    headquarters_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    headquarters_state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    headquarters_country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="India",
    )

    business_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Active",
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="MEDIUM",
    )

    data_source: Mapped[str | None] = mapped_column(
        String(100),
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