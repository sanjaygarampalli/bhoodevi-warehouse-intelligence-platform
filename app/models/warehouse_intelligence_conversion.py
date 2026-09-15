import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WarehouseIntelligenceConversionSource(str, enum.Enum):
    WAREHOUSE_MATCH = "WAREHOUSE_MATCH"
    CAPABILITY_MATCH = "CAPABILITY_MATCH"
    WAREHOUSE_PILOT = "WAREHOUSE_PILOT"


class WarehouseIntelligenceConversionStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONVERTED = "CONVERTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class WarehouseIntelligenceOpportunityConversion(Base):
    __tablename__ = "warehouse_intelligence_opportunity_conversions"
    __table_args__ = (
        CheckConstraint("source_type = 'WAREHOUSE_MATCH' AND warehouse_match_id IS NOT NULL", name="ck_wioc__supported_source"),
        CheckConstraint("status <> 'CONVERTED' OR deal_id IS NOT NULL", name="ck_wioc__converted_deal"),
        Index("ix_wioc__organization__status", "organization_id", "status"),
        Index("ix_wioc__source_type__source", "source_type", "warehouse_match_id"),
        Index("ix_wioc__organization", "organization_id"),
        UniqueConstraint("warehouse_match_id", name="uq_wioc__warehouse_match"),
        UniqueConstraint("deal_id", name="uq_wioc__deal"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    source_type: Mapped[WarehouseIntelligenceConversionSource] = mapped_column(
        Enum(WarehouseIntelligenceConversionSource, name="warehouseintelligenceconversionsource"), nullable=False,
    )
    warehouse_match_id: Mapped[int] = mapped_column(ForeignKey("warehouse_matches.id", ondelete="RESTRICT"), nullable=False)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("deals.id", ondelete="RESTRICT"), nullable=True)
    status: Mapped[WarehouseIntelligenceConversionStatus] = mapped_column(
        Enum(WarehouseIntelligenceConversionStatus, name="warehouseintelligenceconversionstatus"), nullable=False,
    )
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization = relationship("Organization")
    warehouse_match = relationship("WarehouseMatch")
    deal = relationship("Deal")
    created_by_user = relationship("User")