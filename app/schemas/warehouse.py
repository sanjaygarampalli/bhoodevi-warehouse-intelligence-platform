from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.requirement import WarehouseType
from app.models.warehouse import AvailabilityStatus


class WarehouseBase(BaseModel):
    warehouse_name: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)


class WarehouseCreate(WarehouseBase):
    owner_id: int = Field(..., gt=0)
    warehouse_code: str | None = Field(default=None, max_length=50)
    warehouse_type: WarehouseType | None = None
    total_area_sqft: float | None = None
    built_up_area_sqft: float | None = None
    open_area_sqft: float | None = None
    height_ft: float | None = None
    floor_load_kg_sqm: float | None = None
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    country: str | None = Field(default="India", max_length=100)
    postal_code: str | None = Field(default=None, max_length=10)
    latitude: float | None = None
    longitude: float | None = None
    rent_per_month: float | None = None
    currency: str | None = Field(default="INR", max_length=3)
    min_lease_months: int | None = None
    available_from: datetime | None = None
    availability_status: AvailabilityStatus | None = None
    amenities: str | None = Field(default=None, max_length=500)
    certifications: str | None = Field(default=None, max_length=500)
    condition_grade: str | None = Field(default=None, max_length=1)
    occupancy_rate: float | None = None


class WarehouseUpdate(BaseModel):
    warehouse_name: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    warehouse_code: Optional[str] = Field(None, max_length=50)
    warehouse_type: Optional[WarehouseType] = None
    total_area_sqft: Optional[float] = None
    built_up_area_sqft: Optional[float] = None
    open_area_sqft: Optional[float] = None
    height_ft: Optional[float] = None
    floor_load_kg_sqm: Optional[float] = None
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=10)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rent_per_month: Optional[float] = None
    currency: Optional[str] = Field(None, max_length=3)
    min_lease_months: Optional[int] = None
    available_from: Optional[datetime] = None
    availability_status: Optional[AvailabilityStatus] = None
    amenities: Optional[str] = Field(None, max_length=500)
    certifications: Optional[str] = Field(None, max_length=500)
    condition_grade: Optional[str] = Field(None, max_length=1)
    occupancy_rate: Optional[float] = None


class WarehouseResponse(WarehouseBase):
    id: int
    owner_id: int
    warehouse_code: str | None
    warehouse_type: WarehouseType | None
    total_area_sqft: float | None
    built_up_area_sqft: float | None
    open_area_sqft: float | None
    height_ft: float | None
    floor_load_kg_sqm: float | None
    address_line1: str | None
    address_line2: str | None
    country: str | None
    postal_code: str | None
    latitude: float | None
    longitude: float | None
    rent_per_month: float | None
    currency: str | None
    min_lease_months: int | None
    available_from: datetime | None
    availability_status: AvailabilityStatus | None
    amenities: str | None
    certifications: str | None
    condition_grade: str | None
    occupancy_rate: float | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseListResponse(BaseModel):
    warehouses: List[WarehouseResponse]

    model_config = ConfigDict(from_attributes=True)