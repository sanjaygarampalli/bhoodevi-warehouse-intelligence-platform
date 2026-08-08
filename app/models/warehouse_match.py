import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WarehouseMatchStatus(str, enum.Enum):
    AI_RECOMMENDED = "AI_RECOMMENDED"
    SHORTLISTED = "SHORTLISTED"
    PROPOSED = "PROPOSED"
    LEAD_CHOSEN = "LEAD_CHOSEN"
    REJECTED = "REJECTED"
    CONVERTED = "CONVERTED"
    STALE = "STALE"


class MatchedBy(str, enum.Enum):
    AI = "AI"
    MANUAL = "MANUAL"
    HYBRID = "HYBRID"


class WarehouseMatch(Base):
    __tablename__ = "warehouse_matches"
    __table_args__ = (
        Index("ix_warehouse_matches__requirement_id__match_score", "requirement_id", "match_score"),
        Index("ix_warehouse_matches__lead_id__match_score", "lead_id", "match_score"),
        Index("ix_warehouse_matches__warehouse_id__status", "warehouse_id", "status"),
        CheckConstraint(
            "match_score >= 0 AND match_score <= 100",
            name="ck_warehouse_matches__match_score_range",
        ),
        CheckConstraint(
            "status IN ('AI_RECOMMENDED','SHORTLISTED','PROPOSED','LEAD_CHOSEN','REJECTED','CONVERTED','STALE')",
            name="ck_warehouse_matches__status",
        ),
        CheckConstraint(
            "matched_by IN ('AI','MANUAL','HYBRID')",
            name="ck_warehouse_matches__matched_by",
        ),
        # Partial unique indexes match the approved database design exactly:
        # 1. One lead-level match per (lead_id, warehouse_id).
        Index(
            "uq_warehouse_matches__lead__warehouse__partial",
            "lead_id",
            "warehouse_id",
            unique=True,
            sqlite_where=text("requirement_id IS NULL"),
            postgresql_where=text("requirement_id IS NULL"),
        ),
        # 2. One requirement-level match per (requirement_id, warehouse_id).
        Index(
            "uq_warehouse_matches__requirement__warehouse__partial",
            "requirement_id",
            "warehouse_id",
            unique=True,
            sqlite_where=text("requirement_id IS NOT NULL"),
            postgresql_where=text("requirement_id IS NOT NULL"),
        ),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    lead_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    requirement_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    warehouse_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    match_score: Mapped[Numeric] = mapped_column(Numeric(5, 2), nullable=False)

    match_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    geo_distance_km: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)

    transit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    capacity_fit: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    budget_fit: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    requirement_compatibility: Mapped[str | None] = mapped_column(Text, nullable=True)

    match_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)

    concern_reasons: Mapped[str | None] = mapped_column(Text, nullable=True)

    top_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[WarehouseMatchStatus] = mapped_column(
        Enum(WarehouseMatchStatus, name="warehousematchstatus"),
        nullable=False,
        index=True,
    )

    matched_by: Mapped[MatchedBy] = mapped_column(
        Enum(MatchedBy, name="matchedby"),
        nullable=False,
    )

    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="warehouse_matches")

    requirement: Mapped["Requirement | None"] = relationship(
        "Requirement",
        back_populates="warehouse_matches",
    )

    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="matches",
    )

    reviewed_by_user: Mapped["User | None"] = relationship(
        "User",
        back_populates="reviewed_warehouse_matches",
    )