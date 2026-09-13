from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.warehouse_capability import CapabilityStatus


class CapabilityValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Any = None
    status: CapabilityStatus = CapabilityStatus.UNKNOWN
    note: str | None = Field(default=None, max_length=500)


class CapabilityProfileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capabilities: dict[str, CapabilityValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_values(self):
        for name, item in self.capabilities.items():
            if name not in {
                "available_area_sqft", "minimum_leasable_area_sqft", "maximum_leasable_area_sqft",
                "building_type", "flooring_type", "flooring_condition", "clear_height_ft",
                "dock_availability", "number_of_docks", "gate_width_ft", "truck_access",
                "container_access", "road_access_classification", "access_24_7", "power",
                "water", "drainage", "fire_safety", "security", "cctv", "office_space",
                "cold_storage", "temperature_control", "hazardous_material_suitability",
            }:
                raise ValueError(f"Unsupported capability: {name}")
            if isinstance(item.value, (int, float, Decimal)) and item.value < 0:
                raise ValueError(f"{name} cannot be negative")
        return self


class CapabilityProfileResponse(CapabilityProfileWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    warehouse_id: int
    created_at: datetime
    updated_at: datetime