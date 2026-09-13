from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequirementValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Any = None
    priority: str = "PREFERRED"
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_priority(self):
        if self.priority not in {"MANDATORY", "IMPORTANT", "PREFERRED"}:
            raise ValueError("priority must be MANDATORY, IMPORTANT, or PREFERRED")
        return self


class RequirementProfileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirements: dict[str, RequirementValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_values(self):
        allowed = {
            "required_area_min_sqft", "required_area_max_sqft", "preferred_city", "preferred_district",
            "preferred_state", "geographic_notes", "flooring_type", "minimum_gate_width_ft",
            "dock_required", "minimum_clear_height_ft", "truck_access", "container_access",
            "power_required", "water_required", "drainage_required", "security_required",
        }
        for name, item in self.requirements.items():
            if name not in allowed:
                raise ValueError(f"Unsupported requirement: {name}")
            if isinstance(item.value, (int, float, Decimal)) and item.value < 0:
                raise ValueError(f"{name} cannot be negative")
        minimum = self.requirements.get("required_area_min_sqft")
        maximum = self.requirements.get("required_area_max_sqft")
        if minimum and maximum and minimum.value is not None and maximum.value is not None and minimum.value > maximum.value:
            raise ValueError("required_area_min_sqft must be <= required_area_max_sqft")
        return self


class RequirementProfileResponse(RequirementProfileWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime