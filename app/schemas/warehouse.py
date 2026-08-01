from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class WarehouseBase(BaseModel):
    warehouse_name: str = Field(..., max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)


class WarehouseCreate(WarehouseBase):
    owner_id: int = Field(..., gt=0)


class WarehouseUpdate(BaseModel):
    warehouse_name: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)


class WarehouseResponse(WarehouseBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class WarehouseListResponse(BaseModel):
    warehouses: List[WarehouseResponse]

    model_config = ConfigDict(from_attributes=True)