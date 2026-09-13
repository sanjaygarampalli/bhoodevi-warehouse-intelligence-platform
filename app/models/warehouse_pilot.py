import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OperationalStatus(str, enum.Enum):
    READY = "READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    UNDER_PREPARATION = "UNDER_PREPARATION"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"
    INACTIVE = "INACTIVE"


class ListingStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RESERVED = "RESERVED"
    OCCUPIED = "OCCUPIED"
    UNDER_NEGOTIATION = "UNDER_NEGOTIATION"


class MaintenanceChargeType(str, enum.Enum):
    PER_SQFT = "PER_SQFT"
    MONTHLY = "MONTHLY"
    INCLUDED = "INCLUDED"


class RequirementConfidence(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY = "LIKELY"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"


class ValidationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CAPTURED = "CAPTURED"
    VALIDATED = "VALIDATED"
    OUTDATED = "OUTDATED"
    REJECTED = "REJECTED"


class RequirementFlexibility(str, enum.Enum):
    STRICT = "STRICT"
    MODERATE = "MODERATE"
    FLEXIBLE = "FLEXIBLE"


class WarehouseOperationalProfile(Base):
    __tablename__ = "warehouse_operational_profiles"
    __table_args__ = (UniqueConstraint("organization_id", "warehouse_id", name="uq_warehouse_operational_profile_org_warehouse"), Index("ix_warehouse_operational_profiles__warehouse_id", "warehouse_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    site_name: Mapped[str | None] = mapped_column(String(255))
    building_name: Mapped[str | None] = mapped_column(String(255))
    warehouse_category: Mapped[str | None] = mapped_column(String(100))
    construction_type: Mapped[str | None] = mapped_column(String(50))
    building_structure: Mapped[str | None] = mapped_column(String(100))
    building_condition: Mapped[str | None] = mapped_column(String(50))
    year_built: Mapped[int | None] = mapped_column(Integer)
    number_of_blocks: Mapped[int | None] = mapped_column(Integer)
    number_of_floors: Mapped[int | None] = mapped_column(Integer)
    usable_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_plot_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    office_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    parking_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    approach_road_width_ft: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    approach_road_surface: Mapped[str | None] = mapped_column(String(50))
    truck_access: Mapped[str | None] = mapped_column(String(50))
    turning_radius_adequate: Mapped[bool | None] = mapped_column(Boolean)
    vehicle_parking_available: Mapped[bool | None] = mapped_column(Boolean)
    truck_parking_capacity: Mapped[int | None] = mapped_column(Integer)
    loading_vehicle_access: Mapped[bool | None] = mapped_column(Boolean)
    container_access: Mapped[bool | None] = mapped_column(Boolean)
    loading_bays_count: Mapped[int | None] = mapped_column(Integer)
    dock_levelers_count: Mapped[int | None] = mapped_column(Integer)
    dock_height_ft: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    ground_level_loading_available: Mapped[bool | None] = mapped_column(Boolean)
    covered_loading_area: Mapped[bool | None] = mapped_column(Boolean)
    loading_platform_available: Mapped[bool | None] = mapped_column(Boolean)
    loading_equipment_available: Mapped[bool | None] = mapped_column(Boolean)
    forklift_available: Mapped[bool | None] = mapped_column(Boolean)
    forklift_capacity_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pallet_handling_available: Mapped[bool | None] = mapped_column(Boolean)
    material_handling_notes: Mapped[str | None] = mapped_column(Text)
    power_connection_available: Mapped[bool | None] = mapped_column(Boolean)
    sanctioned_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    backup_power_available: Mapped[bool | None] = mapped_column(Boolean)
    generator_capacity_kva: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    transformer_available: Mapped[bool | None] = mapped_column(Boolean)
    water_supply_available: Mapped[bool | None] = mapped_column(Boolean)
    drainage_available: Mapped[bool | None] = mapped_column(Boolean)
    internet_available: Mapped[bool | None] = mapped_column(Boolean)
    telecom_available: Mapped[bool | None] = mapped_column(Boolean)
    fire_safety_system: Mapped[dict[str, Any] | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    fire_extinguishers_available: Mapped[bool | None] = mapped_column(Boolean)
    hydrant_system_available: Mapped[bool | None] = mapped_column(Boolean)
    sprinkler_system_available: Mapped[bool | None] = mapped_column(Boolean)
    fire_noc_available: Mapped[bool | None] = mapped_column(Boolean)
    emergency_exits_available: Mapped[bool | None] = mapped_column(Boolean)
    emergency_lighting_available: Mapped[bool | None] = mapped_column(Boolean)
    security_available: Mapped[bool | None] = mapped_column(Boolean)
    cctv_available: Mapped[bool | None] = mapped_column(Boolean)
    boundary_security: Mapped[bool | None] = mapped_column(Boolean)
    security_notes: Mapped[str | None] = mapped_column(Text)
    flooring_type: Mapped[str | None] = mapped_column(String(50))
    floor_condition: Mapped[str | None] = mapped_column(String(50))
    floor_levelness: Mapped[str | None] = mapped_column(String(50))
    floor_load_capacity: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pallet_storage_supported: Mapped[bool | None] = mapped_column(Boolean)
    racking_supported: Mapped[bool | None] = mapped_column(Boolean)
    maximum_rack_height_ft: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    storage_type_supported: Mapped[str | None] = mapped_column(String(50))
    operational_status: Mapped[OperationalStatus | None] = mapped_column(Enum(OperationalStatus, name="operationalstatus"))
    available_for_site_visit: Mapped[bool | None] = mapped_column(Boolean)
    site_visit_notice_hours: Mapped[int | None] = mapped_column(Integer)
    operational_notes: Mapped[str | None] = mapped_column(Text)
    improvement_plan: Mapped[str | None] = mapped_column(Text)
    improvement_budget_estimate: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class WarehouseCommercialProfile(Base):
    __tablename__ = "warehouse_commercial_profiles"
    __table_args__ = (UniqueConstraint("organization_id", "warehouse_id", name="uq_warehouse_commercial_profile_org_warehouse"), Index("ix_warehouse_commercial_profiles__warehouse_id", "warehouse_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True)
    listing_status: Mapped[ListingStatus | None] = mapped_column(Enum(ListingStatus, name="listingstatus"))
    available_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    minimum_leasable_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    maximum_leasable_area_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    available_from: Mapped[date | None] = mapped_column(Date)
    lease_term_min_months: Mapped[int | None] = mapped_column(Integer)
    lease_term_max_months: Mapped[int | None] = mapped_column(Integer)
    expected_rent_per_sqft: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    expected_monthly_rent: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    security_deposit_months: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    escalation_percentage: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    escalation_frequency_months: Mapped[int | None] = mapped_column(Integer)
    maintenance_charge: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    maintenance_charge_type: Mapped[MaintenanceChargeType | None] = mapped_column(Enum(MaintenanceChargeType, name="maintenancechargetype"))
    property_tax_included: Mapped[bool | None] = mapped_column(Boolean)
    electricity_terms: Mapped[str | None] = mapped_column(Text)
    water_terms: Mapped[str | None] = mapped_column(Text)
    rent_negotiable: Mapped[bool | None] = mapped_column(Boolean)
    lease_term_negotiable: Mapped[bool | None] = mapped_column(Boolean)
    fitout_support_available: Mapped[bool | None] = mapped_column(Boolean)
    client_specific_modifications_possible: Mapped[bool | None] = mapped_column(Boolean)
    modification_notes: Mapped[str | None] = mapped_column(Text)
    commercial_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")


class WarehouseRequirementAssessment(Base):
    __tablename__ = "warehouse_requirement_assessments"
    __table_args__ = (UniqueConstraint("organization_id", "company_id", name="uq_warehouse_requirement_assessment_org_company"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_source: Mapped[str | None] = mapped_column(String(50))
    captured_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    requirement_confidence: Mapped[RequirementConfidence] = mapped_column(Enum(RequirementConfidence, name="requirementconfidence"), nullable=False, default=RequirementConfidence.UNVERIFIED)
    budget_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    budget_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    preferred_rent_per_sqft: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    preferred_lease_months: Mapped[int | None] = mapped_column(Integer)
    deposit_preference: Mapped[str | None] = mapped_column(String(100))
    move_in_target_date: Mapped[date | None] = mapped_column(Date)
    preferred_city: Mapped[str | None] = mapped_column(String(100))
    preferred_state: Mapped[str | None] = mapped_column(String(100))
    preferred_micro_markets: Mapped[list[str] | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    maximum_distance_from_city_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    maximum_distance_from_highway_km: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    location_notes: Mapped[str | None] = mapped_column(Text)
    requirement_flexibility: Mapped[RequirementFlexibility | None] = mapped_column(Enum(RequirementFlexibility, name="requirementflexibility"))
    negotiable_requirements: Mapped[list[str] | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    possible_tradeoffs: Mapped[list[str] | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    client_priority_notes: Mapped[str | None] = mapped_column(Text)
    validation_status: Mapped[ValidationStatus] = mapped_column(Enum(ValidationStatus, name="validationstatus"), nullable=False, default=ValidationStatus.DRAFT)
    validated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)
    validation_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    company: Mapped["Company"] = relationship("Company")