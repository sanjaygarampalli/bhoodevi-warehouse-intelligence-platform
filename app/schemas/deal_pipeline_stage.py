from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DealPipelineStageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    organization_id: int = Field(gt=0)
    stage_name: str = Field(min_length=1, max_length=120)
    stage_key: str = Field(min_length=1, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$")
    description: str | None = None
    stage_order: int = Field(ge=0)
    is_active: bool = True
    is_terminal: bool = False
    is_won: bool = False
    is_lost: bool = False


class DealPipelineStageUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    stage_name: str | None = Field(None, min_length=1, max_length=120)
    stage_key: str | None = Field(None, min_length=1, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$")
    description: str | None = None
    stage_order: int | None = Field(None, ge=0)
    is_active: bool | None = None
    is_terminal: bool | None = None
    is_won: bool | None = None
    is_lost: bool | None = None

    @field_validator("stage_name", "stage_key", "stage_order", "is_active", "is_terminal", "is_won", "is_lost")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class DealPipelineStageResponse(DealPipelineStageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime