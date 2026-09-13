from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.warehouse_pilot import (
    ListingStatus, MaintenanceChargeType, OperationalStatus, RequirementConfidence,
    RequirementFlexibility, ValidationStatus,
)


class PilotBase(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


OPERATIONAL_FIELDS = {
    "site_name", "building_name", "warehouse_category", "construction_type", "building_structure", "building_condition", "year_built", "number_of_blocks", "number_of_floors", "usable_area_sqft", "total_plot_area_sqft", "office_area_sqft", "parking_area_sqft", "approach_road_width_ft", "approach_road_surface", "truck_access", "turning_radius_adequate", "vehicle_parking_available", "truck_parking_capacity", "loading_vehicle_access", "container_access", "loading_bays_count", "dock_levelers_count", "dock_height_ft", "ground_level_loading_available", "covered_loading_area", "loading_platform_available", "loading_equipment_available", "forklift_available", "forklift_capacity_kg", "pallet_handling_available", "material_handling_notes", "power_connection_available", "sanctioned_power_kw", "backup_power_available", "generator_capacity_kva", "transformer_available", "water_supply_available", "drainage_available", "internet_available", "telecom_available", "fire_safety_system", "fire_extinguishers_available", "hydrant_system_available", "sprinkler_system_available", "fire_noc_available", "emergency_exits_available", "emergency_lighting_available", "security_available", "cctv_available", "boundary_security", "security_notes", "flooring_type", "floor_condition", "floor_levelness", "floor_load_capacity", "pallet_storage_supported", "racking_supported", "maximum_rack_height_ft", "storage_type_supported", "operational_status", "available_for_site_visit", "site_visit_notice_hours", "operational_notes", "improvement_plan", "improvement_budget_estimate",
}


class OperationalProfileWrite(PilotBase):
    site_name: str | None = None
    building_name: str | None = None
    warehouse_category: str | None = None
    construction_type: str | None = None
    building_structure: str | None = None
    building_condition: str | None = None
    year_built: int | None = Field(None, ge=1800, le=2200)
    number_of_blocks: int | None = Field(None, ge=0)
    number_of_floors: int | None = Field(None, ge=0)
    usable_area_sqft: Decimal | None = Field(None, ge=0)
    total_plot_area_sqft: Decimal | None = Field(None, ge=0)
    office_area_sqft: Decimal | None = Field(None, ge=0)
    parking_area_sqft: Decimal | None = Field(None, ge=0)
    approach_road_width_ft: Decimal | None = Field(None, ge=0)
    approach_road_surface: str | None = None
    truck_access: str | None = None
    turning_radius_adequate: bool | None = None
    vehicle_parking_available: bool | None = None
    truck_parking_capacity: int | None = Field(None, ge=0)
    loading_vehicle_access: bool | None = None
    container_access: bool | None = None
    loading_bays_count: int | None = Field(None, ge=0)
    dock_levelers_count: int | None = Field(None, ge=0)
    dock_height_ft: Decimal | None = Field(None, ge=0)
    ground_level_loading_available: bool | None = None
    covered_loading_area: bool | None = None
    loading_platform_available: bool | None = None
    loading_equipment_available: bool | None = None
    forklift_available: bool | None = None
    forklift_capacity_kg: Decimal | None = Field(None, ge=0)
    pallet_handling_available: bool | None = None
    material_handling_notes: str | None = None
    power_connection_available: bool | None = None
    sanctioned_power_kw: Decimal | None = Field(None, ge=0)
    backup_power_available: bool | None = None
    generator_capacity_kva: Decimal | None = Field(None, ge=0)
    transformer_available: bool | None = None
    water_supply_available: bool | None = None
    drainage_available: bool | None = None
    internet_available: bool | None = None
    telecom_available: bool | None = None
    fire_safety_system: dict[str, Any] | None = None
    fire_extinguishers_available: bool | None = None
    hydrant_system_available: bool | None = None
    sprinkler_system_available: bool | None = None
    fire_noc_available: bool | None = None
    emergency_exits_available: bool | None = None
    emergency_lighting_available: bool | None = None
    security_available: bool | None = None
    cctv_available: bool | None = None
    boundary_security: bool | None = None
    security_notes: str | None = None
    flooring_type: str | None = None
    floor_condition: str | None = None
    floor_levelness: str | None = None
    floor_load_capacity: Decimal | None = Field(None, ge=0)
    pallet_storage_supported: bool | None = None
    racking_supported: bool | None = None
    maximum_rack_height_ft: Decimal | None = Field(None, ge=0)
    storage_type_supported: str | None = None
    operational_status: OperationalStatus | None = None
    available_for_site_visit: bool | None = None
    site_visit_notice_hours: int | None = Field(None, ge=0)
    operational_notes: str | None = None
    improvement_plan: str | None = None
    improvement_budget_estimate: Decimal | None = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_profile(self):
        if self.forklift_available is False and self.forklift_capacity_kg and self.forklift_capacity_kg > 0:
            raise ValueError("forklift_capacity_kg cannot be positive when forklift_available is false")
        if self.usable_area_sqft and self.total_plot_area_sqft and self.usable_area_sqft > self.total_plot_area_sqft:
            raise ValueError("usable_area_sqft must not exceed total_plot_area_sqft")
        return self


class OperationalProfileResponse(OperationalProfileWrite):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    id: int
    organization_id: int
    warehouse_id: int
    created_at: datetime
    updated_at: datetime


class CommercialProfileWrite(PilotBase):
    listing_status: ListingStatus | None = None
    available_area_sqft: Decimal | None = Field(None, ge=0)
    minimum_leasable_area_sqft: Decimal | None = Field(None, ge=0)
    maximum_leasable_area_sqft: Decimal | None = Field(None, ge=0)
    available_from: date | None = None
    lease_term_min_months: int | None = Field(None, ge=0)
    lease_term_max_months: int | None = Field(None, ge=0)
    expected_rent_per_sqft: Decimal | None = Field(None, ge=0)
    expected_monthly_rent: Decimal | None = Field(None, ge=0)
    security_deposit_months: Decimal | None = Field(None, ge=0)
    escalation_percentage: Decimal | None = Field(None, ge=0)
    escalation_frequency_months: int | None = Field(None, ge=0)
    maintenance_charge: Decimal | None = Field(None, ge=0)
    maintenance_charge_type: MaintenanceChargeType | None = None
    property_tax_included: bool | None = None
    electricity_terms: str | None = None
    water_terms: str | None = None
    rent_negotiable: bool | None = None
    lease_term_negotiable: bool | None = None
    fitout_support_available: bool | None = None
    client_specific_modifications_possible: bool | None = None
    modification_notes: str | None = None
    commercial_notes: str | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.minimum_leasable_area_sqft and self.maximum_leasable_area_sqft and self.minimum_leasable_area_sqft > self.maximum_leasable_area_sqft:
            raise ValueError("minimum_leasable_area_sqft must not exceed maximum_leasable_area_sqft")
        if self.lease_term_min_months and self.lease_term_max_months and self.lease_term_min_months > self.lease_term_max_months:
            raise ValueError("lease_term_min_months must not exceed lease_term_max_months")
        return self


class CommercialProfileResponse(CommercialProfileWrite):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    id: int
    organization_id: int
    warehouse_id: int
    created_at: datetime
    updated_at: datetime


class RequirementAssessmentWrite(PilotBase):
    requirement_source: str | None = None
    captured_by_user_id: int | None = Field(None, ge=1)
    requirement_confidence: RequirementConfidence = RequirementConfidence.UNVERIFIED
    budget_min: Decimal | None = Field(None, ge=0)
    budget_max: Decimal | None = Field(None, ge=0)
    preferred_rent_per_sqft: Decimal | None = Field(None, ge=0)
    preferred_lease_months: int | None = Field(None, ge=0)
    deposit_preference: str | None = None
    move_in_target_date: date | None = None
    preferred_city: str | None = None
    preferred_state: str | None = None
    preferred_micro_markets: list[str] | None = None
    maximum_distance_from_city_km: Decimal | None = Field(None, ge=0)
    maximum_distance_from_highway_km: Decimal | None = Field(None, ge=0)
    location_notes: str | None = None
    requirement_flexibility: RequirementFlexibility | None = None
    negotiable_requirements: list[str] | None = None
    possible_tradeoffs: list[str] | None = None
    client_priority_notes: str | None = None
    validation_status: ValidationStatus = ValidationStatus.DRAFT
    validated_by_user_id: int | None = Field(None, ge=1)
    validated_at: datetime | None = None
    validation_notes: str | None = None

    @model_validator(mode="after")
    def validate_budget(self):
        if self.budget_min and self.budget_max and self.budget_min > self.budget_max:
            raise ValueError("budget_min must not exceed budget_max")
        return self


class RequirementAssessmentResponse(RequirementAssessmentWrite):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    id: int
    organization_id: int
    company_id: int
    captured_at: datetime
    created_at: datetime
    updated_at: datetime


class PilotAssessmentRequest(PilotBase):
    warehouse_id: int = Field(ge=1)
    company_id: int = Field(ge=1)


class PilotAssessmentResponse(PilotBase):
    warehouse_id: int
    company_id: int
    technical_score: int | None
    technical_classification: str
    mandatory_gaps: list[str]
    planned_capabilities: list[str]
    factor_results: list[dict[str, Any]]
    commercial_fit: str
    commercial_reasons: list[str]
    availability_fit: str
    availability_reasons: list[str]
    operational_readiness: str
    operational_reasons: list[str]
    requirement_confidence: str
    overall_classification: str
    explanation: list[str]