from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.decision_maker import (
    DecisionLevel,
    DecisionMakerStatus,
    PreferredContact,
)


class DecisionMakerCreate(BaseModel):
    company_id: int
    full_name: str = Field(min_length=1, max_length=255)
    designation: str = Field(min_length=1, max_length=255)
    decision_level: DecisionLevel = DecisionLevel.OTHER
    preferred_contact: PreferredContact | None = None
    decision_maker_status: DecisionMakerStatus = DecisionMakerStatus.NEW
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    linkedin_url: str | None = Field(default=None, max_length=255)
    is_primary_contact: bool = False
    last_contacted_at: datetime | None = None
    notes: str | None = None


class DecisionMakerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    designation: str | None = Field(default=None, min_length=1, max_length=255)
    decision_level: DecisionLevel | None = None
    preferred_contact: PreferredContact | None = None
    decision_maker_status: DecisionMakerStatus | None = None
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    linkedin_url: str | None = Field(default=None, max_length=255)
    is_primary_contact: bool | None = None
    last_contacted_at: datetime | None = None
    notes: str | None = None


class DecisionMakerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    full_name: str
    designation: str
    decision_level: DecisionLevel
    preferred_contact: PreferredContact | None
    decision_maker_status: DecisionMakerStatus
    email: str | None
    phone: str | None
    linkedin_url: str | None
    is_primary_contact: bool
    last_contacted_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime