import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.lead import MoveInTimeframe


class WarehouseType(str, enum.Enum):
    COVERED = "COVERED"
    OPEN_YARD = "OPEN_YARD"
    COLD_STORAGE = "COLD_STORAGE"
    BONDED = "BONDED"
    MULTIPURPOSE = "MULTIPURPOSE"
    CONTAINER = "CONTAINER"
    TRANSIT = "TRANSIT"
    OTHER = "OTHER"


class RequirementStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Requirement(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Space
    required_builtup_area: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    required_open_area: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    minimum_area: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    maximum_area: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Business
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    goods_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    storage_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    compliance_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location
    preferred_state: Mapped[str | None] = mapped_column(String(100), nullable=True)

    preferred_city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    preferred_locality: Mapped[str | None] = mapped_column(String(150), nullable=True)

    preferred_pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)

    radius_km: Mapped[Numeric | None] = mapped_column(Numeric(8, 2), nullable=True)

    latitude: Mapped[Numeric | None] = mapped_column(Numeric(10, 7), nullable=True)

    longitude: Mapped[Numeric | None] = mapped_column(Numeric(10, 7), nullable=True)

    # Financial
    budget_per_sqft: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    lease_duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    security_deposit_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    preferred_lease_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    escalation_percentage: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Warehouse
    warehouse_type: Mapped[WarehouseType | None] = mapped_column(Enum(WarehouseType, name="warehousetype"), nullable=True)

    # Technical
    required_clear_height: Mapped[Numeric | None] = mapped_column(Numeric(8, 2), nullable=True)

    required_floor_load: Mapped[Numeric | None] = mapped_column(Numeric(8, 2), nullable=True)

    required_power_load: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)

    required_docks: Mapped[int | None] = mapped_column(Integer, nullable=True)

    truck_parking_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    rail_connectivity_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    fire_noc_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    temperature_controlled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    loading_bays_required: Mapped[int | None] = mapped_column(Integer, nullable=True)

    dock_level_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    ground_level_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    office_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    labour_required: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Operations
    operating_hours: Mapped[str | None] = mapped_column(String(50), nullable=True)

    expected_monthly_dispatch: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    expected_monthly_receipts: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Timeline
    move_in_timeframe: Mapped[MoveInTimeframe | None] = mapped_column(Enum(MoveInTimeframe, name="moveintimeframe"), nullable=True)

    # Status
    requirement_status: Mapped[RequirementStatus] = mapped_column(Enum(RequirementStatus, name="requirementstatus"), nullable=False, default=RequirementStatus.DRAFT, index=True)

    # AI placeholders (database only — no AI logic in Sprint 4)
    ai_match_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    requirement_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    priority_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    confidence_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead: Mapped["Lead"] = relationship("Lead", back_populates="requirements")
    warehouse_matches: Mapped[list["WarehouseMatch"]] = relationship(
        "WarehouseMatch", back_populates="requirement"
    )
