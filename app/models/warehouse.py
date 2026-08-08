import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.requirement import WarehouseType


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    PARTIALLY_OCCUPIED = "PARTIALLY_OCCUPIED"
    OCCUPIED = "OCCUPIED"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    INACTIVE = "INACTIVE"


class Warehouse(Base):
    __tablename__ = "warehouses"
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    warehouse_name: Mapped[str] = mapped_column(String(255), nullable=False)

    warehouse_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        index=True,
    )

    warehouse_type: Mapped[WarehouseType | None] = mapped_column(
        Enum(WarehouseType, name="warehousetype"), nullable=True, index=True
    )

    # Size
    total_area_sqft: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    built_up_area_sqft: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    open_area_sqft: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    # Technical
    height_ft: Mapped[Numeric | None] = mapped_column(Numeric(8, 2), nullable=True)

    floor_load_kg_sqm: Mapped[Numeric | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Location
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)

    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)

    city: Mapped[str] = mapped_column(String(100), nullable=False)

    state: Mapped[str] = mapped_column(String(100), nullable=False)

    country: Mapped[str | None] = mapped_column(String(100), nullable=True, default="India")

    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    latitude: Mapped[Numeric | None] = mapped_column(Numeric(10, 7), nullable=True)

    longitude: Mapped[Numeric | None] = mapped_column(Numeric(10, 7), nullable=True)

    # Financial
    rent_per_month: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="INR")

    min_lease_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Availability
    available_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    availability_status: Mapped[AvailabilityStatus | None] = mapped_column(
        Enum(AvailabilityStatus, name="availabilitystatus"), nullable=True
    )

    # Amenities & condition
    amenities: Mapped[str | None] = mapped_column(String(500), nullable=True)

    certifications: Mapped[str | None] = mapped_column(String(500), nullable=True)

    condition_grade: Mapped[str | None] = mapped_column(String(1), nullable=True)

    occupancy_rate: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Ownership
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="warehouses")
    matches: Mapped[list["WarehouseMatch"]] = relationship(
        "WarehouseMatch", back_populates="warehouse"
    )


from app.models.warehouse_match import WarehouseMatch  # noqa: E402,F401