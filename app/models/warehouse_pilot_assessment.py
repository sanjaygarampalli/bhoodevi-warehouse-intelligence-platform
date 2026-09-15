from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WarehousePilotAssessment(Base):
    """Immutable historical output of a Warehouse Pilot evaluation."""

    __tablename__ = "warehouse_pilot_assessments"
    __table_args__ = (
        Index("ix_wpa__organization__assessed_at", "organization_id", "assessed_at"),
        Index("ix_wpa__company__assessed_at", "company_id", "assessed_at"),
        Index("ix_wpa__warehouse__assessed_at", "warehouse_id", "assessed_at"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False, index=True)
    assessed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    capability_profile_id: Mapped[int | None] = mapped_column(ForeignKey("warehouse_capability_profiles.id", ondelete="RESTRICT"), nullable=True)
    company_requirement_profile_id: Mapped[int | None] = mapped_column(ForeignKey("company_warehouse_requirement_profiles.id", ondelete="RESTRICT"), nullable=True)
    operational_profile_id: Mapped[int | None] = mapped_column(ForeignKey("warehouse_operational_profiles.id", ondelete="RESTRICT"), nullable=True)
    commercial_profile_id: Mapped[int | None] = mapped_column(ForeignKey("warehouse_commercial_profiles.id", ondelete="RESTRICT"), nullable=True)
    requirement_assessment_id: Mapped[int | None] = mapped_column(ForeignKey("warehouse_requirement_assessments.id", ondelete="RESTRICT"), nullable=True)
    evaluation_version: Mapped[str] = mapped_column(String(30), nullable=False, default="v1")
    overall_classification: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    result_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization")
    company = relationship("Company")
    warehouse = relationship("Warehouse")
    assessed_by_user = relationship("User")
    capability_profile = relationship("WarehouseCapabilityProfile")
    company_requirement_profile = relationship("CompanyWarehouseRequirementProfile")
    operational_profile = relationship("WarehouseOperationalProfile")
    commercial_profile = relationship("WarehouseCommercialProfile")
    requirement_assessment = relationship("WarehouseRequirementAssessment")