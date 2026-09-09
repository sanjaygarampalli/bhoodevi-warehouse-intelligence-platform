from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Industry(Base):
    __tablename__ = "industries"
    __table_args__ = (
        UniqueConstraint("code", name="uq_industries__code"),
        UniqueConstraint("name", name="uq_industries__name"),
        Index("ix_industries__category", "category"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )