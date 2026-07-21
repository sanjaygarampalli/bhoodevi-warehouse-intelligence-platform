from pydantic import BaseModel, ConfigDict


class WarehouseBase(BaseModel):
    warehouse_name: str
    city: str
    state: str


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    warehouse_name: str | None = None
    city: str | None = None
    state: str | None = None


class WarehouseResponse(WarehouseBase):
    id: int

    model_config = ConfigDict(from_attributes=True)