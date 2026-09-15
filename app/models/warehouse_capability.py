import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CapabilityStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    PLANNED = "PLANNED"
    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class WarehouseCapabilityProfile(Base):
    __tablename__ = "warehouse_capability_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "warehouse_id", name="uq_warehouse_capability_profile_org_warehouse"),
        Index("ix_warehouse_capability_profiles__organization_id", "organization_id"),
        Index("ix_warehouse_capability_profiles__warehouse_id", "warehouse_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")