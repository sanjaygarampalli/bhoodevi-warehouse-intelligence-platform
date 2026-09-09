from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IndustryBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class IndustryCreate(IndustryBase):
    pass


class IndustryUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("code", "name", "is_active")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class IndustryResponse(IndustryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)