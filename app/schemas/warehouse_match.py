from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.warehouse_match import MatchedBy, WarehouseMatchStatus
from app.services.warehouse_matching_rules import WarehouseMatchLevel, classify_match


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

    @computed_field
    @property
    def match_level(self) -> WarehouseMatchLevel:
        return classify_match(self.match_score)

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


class WarehouseMatchReason(BaseModel):
    factor: str
    points: int = Field(ge=0, le=100)
    maximum_points: int = Field(ge=0, le=100)
    explanation: str


class WarehouseMatchAdjustment(BaseModel):
    factor: str
    points: int = Field(le=0)
    score_cap: int = Field(ge=0, le=100)
    explanation: str


class WarehouseMatchResult(BaseModel):
    warehouse_id: int
    warehouse_name: str
    match_rank: int = Field(default=1, ge=1)
    match_score: int = Field(ge=0, le=100)
    match_level: WarehouseMatchLevel
    reasons: list[WarehouseMatchReason]
    adjustments: list[WarehouseMatchAdjustment]
    warnings: list[str]
    existing_match_id: int | None = None
    existing_match_status: WarehouseMatchStatus | None = None


class WarehouseMatchRecommendationResponse(BaseModel):
    requirement_id: int
    lead_id: int
    scoring_version: str
    candidates_evaluated: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    matches: list[WarehouseMatchResult]
    warnings: list[str]


class WarehouseMatchGenerationResponse(BaseModel):
    requirement_id: int
    scoring_version: str
    candidates_evaluated: int = Field(ge=0)
    created: int = Field(ge=0)
    refreshed: int = Field(ge=0)
    stale: int = Field(ge=0)
    preserved: int = Field(ge=0)
    warnings: list[str]