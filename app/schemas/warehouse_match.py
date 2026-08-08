from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.warehouse_match import MatchedBy, WarehouseMatchStatus


class WarehouseMatchCreate(BaseModel):
    lead_id: int = Field(..., gt=0)
    warehouse_id: int = Field(..., gt=0)
    status: WarehouseMatchStatus
    matched_by: MatchedBy
    requirement_id: int | None = Field(default=None, gt=0)
    match_score: float = Field(..., ge=0, le=100)
    match_rank: int | None = None
    geo_distance_km: float | None = None
    transit_days: int | None = None
    capacity_fit: float | None = Field(default=None, ge=0, le=100)
    budget_fit: float | None = Field(default=None, ge=0, le=100)
    requirement_compatibility: str | None = None
    match_reasons: str | None = None
    concern_reasons: str | None = None
    top_reason: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    reviewed_by_user_id: int | None = Field(default=None, gt=0)
    reviewed_at: datetime | None = None
    notes: str | None = None


class WarehouseMatchUpdate(BaseModel):
    lead_id: int | None = Field(default=None, gt=0)
    warehouse_id: int | None = Field(default=None, gt=0)
    requirement_id: int | None = Field(default=None, gt=0)
    status: WarehouseMatchStatus | None = None
    matched_by: MatchedBy | None = None
    match_score: float | None = Field(default=None, ge=0, le=100)
    match_rank: int | None = None
    geo_distance_km: float | None = None
    transit_days: int | None = None
    capacity_fit: float | None = Field(default=None, ge=0, le=100)
    budget_fit: float | None = Field(default=None, ge=0, le=100)
    requirement_compatibility: str | None = None
    match_reasons: str | None = None
    concern_reasons: str | None = None
    top_reason: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    reviewed_by_user_id: int | None = Field(default=None, gt=0)
    reviewed_at: datetime | None = None
    notes: str | None = None


class WarehouseMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    requirement_id: int | None
    warehouse_id: int
    match_score: float
    match_rank: int | None
    geo_distance_km: float | None
    transit_days: int | None
    capacity_fit: float | None
    budget_fit: float | None
    requirement_compatibility: str | None
    match_reasons: str | None
    concern_reasons: str | None
    top_reason: str | None
    status: WarehouseMatchStatus
    matched_by: MatchedBy
    model_id: str | None
    model_version: str | None
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime