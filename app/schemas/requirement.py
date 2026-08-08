from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.lead import MoveInTimeframe
from app.models.requirement import RequirementStatus, WarehouseType


class RequirementCreate(BaseModel):
    lead_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    required_builtup_area: float | None = None
    required_open_area: float | None = None
    minimum_area: float | None = None
    maximum_area: float | None = None
    industry: str | None = Field(default=None, max_length=100)
    goods_type: str | None = Field(default=None, max_length=100)
    storage_type: str | None = Field(default=None, max_length=50)
    compliance_requirements: str | None = None
    preferred_state: str | None = Field(default=None, max_length=100)
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_locality: str | None = Field(default=None, max_length=150)
    preferred_pincode: str | None = Field(default=None, max_length=10)
    radius_km: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    budget_per_sqft: float | None = None
    lease_duration_months: int | None = None
    security_deposit_months: int | None = None
    preferred_lease_type: str | None = Field(default=None, max_length=30)
    escalation_percentage: float | None = None
    warehouse_type: WarehouseType | None = None
    required_clear_height: float | None = None
    required_floor_load: float | None = None
    required_power_load: float | None = None
    required_docks: int | None = None
    truck_parking_required: bool | None = None
    rail_connectivity_required: bool | None = None
    fire_noc_required: bool | None = None
    temperature_controlled: bool | None = None
    loading_bays_required: int | None = None
    dock_level_required: bool | None = None
    ground_level_required: bool | None = None
    office_required: bool | None = None
    labour_required: bool | None = None
    operating_hours: str | None = Field(default=None, max_length=50)
    expected_monthly_dispatch: float | None = None
    expected_monthly_receipts: float | None = None
    move_in_timeframe: MoveInTimeframe | None = None
    requirement_status: RequirementStatus = RequirementStatus.DRAFT
    ai_match_score: float | None = None
    requirement_score: float | None = None
    priority_score: float | None = None
    confidence_score: float | None = None


class RequirementUpdate(BaseModel):
    lead_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    required_builtup_area: float | None = None
    required_open_area: float | None = None
    minimum_area: float | None = None
    maximum_area: float | None = None
    industry: str | None = Field(default=None, max_length=100)
    goods_type: str | None = Field(default=None, max_length=100)
    storage_type: str | None = Field(default=None, max_length=50)
    compliance_requirements: str | None = None
    preferred_state: str | None = Field(default=None, max_length=100)
    preferred_city: str | None = Field(default=None, max_length=100)
    preferred_locality: str | None = Field(default=None, max_length=150)
    preferred_pincode: str | None = Field(default=None, max_length=10)
    radius_km: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    budget_per_sqft: float | None = None
    lease_duration_months: int | None = None
    security_deposit_months: int | None = None
    preferred_lease_type: str | None = Field(default=None, max_length=30)
    escalation_percentage: float | None = None
    warehouse_type: WarehouseType | None = None
    required_clear_height: float | None = None
    required_floor_load: float | None = None
    required_power_load: float | None = None
    required_docks: int | None = None
    truck_parking_required: bool | None = None
    rail_connectivity_required: bool | None = None
    fire_noc_required: bool | None = None
    temperature_controlled: bool | None = None
    loading_bays_required: int | None = None
    dock_level_required: bool | None = None
    ground_level_required: bool | None = None
    office_required: bool | None = None
    labour_required: bool | None = None
    operating_hours: str | None = Field(default=None, max_length=50)
    expected_monthly_dispatch: float | None = None
    expected_monthly_receipts: float | None = None
    move_in_timeframe: MoveInTimeframe | None = None
    requirement_status: RequirementStatus | None = None
    ai_match_score: float | None = None
    requirement_score: float | None = None
    priority_score: float | None = None
    confidence_score: float | None = None


class RequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    title: str
    description: str | None
    required_builtup_area: float | None
    required_open_area: float | None
    minimum_area: float | None
    maximum_area: float | None
    industry: str | None
    goods_type: str | None
    storage_type: str | None
    compliance_requirements: str | None
    preferred_state: str | None
    preferred_city: str | None
    preferred_locality: str | None
    preferred_pincode: str | None
    radius_km: float | None
    latitude: float | None
    longitude: float | None
    budget_per_sqft: float | None
    lease_duration_months: int | None
    security_deposit_months: int | None
    preferred_lease_type: str | None
    escalation_percentage: float | None
    warehouse_type: WarehouseType | None
    required_clear_height: float | None
    required_floor_load: float | None
    required_power_load: float | None
    required_docks: int | None
    truck_parking_required: bool | None
    rail_connectivity_required: bool | None
    fire_noc_required: bool | None
    temperature_controlled: bool | None
    loading_bays_required: int | None
    dock_level_required: bool | None
    ground_level_required: bool | None
    office_required: bool | None
    labour_required: bool | None
    operating_hours: str | None
    expected_monthly_dispatch: float | None
    expected_monthly_receipts: float | None
    move_in_timeframe: MoveInTimeframe | None
    requirement_status: RequirementStatus
    ai_match_score: float | None
    requirement_score: float | None
    priority_score: float | None
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime