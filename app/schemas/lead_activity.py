from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.lead_activity import (
    ActivityChannel,
    ActivityOutcome,
    ActivitySourceType,
    ActivityStatus,
    ActivityType,
)


class LeadActivityCreate(BaseModel):
    lead_id: int
    activity_type: ActivityType
    subject: str = Field(min_length=1, max_length=255)
    description: str | None = None
    activity_date: datetime | None = None
    next_followup_date: datetime | None = None
    status: ActivityStatus = ActivityStatus.SCHEDULED
    outcome: ActivityOutcome | None = None
    performed_by: int | None = None
    channel: ActivityChannel | None = None
    duration_minutes: int | None = None
    activity_source_type: ActivitySourceType | None = None
    activity_source_id: int | None = None


class LeadActivityUpdate(BaseModel):
    lead_id: int | None = None
    activity_type: ActivityType | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    activity_date: datetime | None = None
    next_followup_date: datetime | None = None
    status: ActivityStatus | None = None
    outcome: ActivityOutcome | None = None
    performed_by: int | None = None
    channel: ActivityChannel | None = None
    duration_minutes: int | None = None
    activity_source_type: ActivitySourceType | None = None
    activity_source_id: int | None = None


class LeadActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    activity_type: ActivityType
    subject: str
    description: str | None
    activity_date: datetime
    next_followup_date: datetime | None
    status: ActivityStatus
    outcome: ActivityOutcome | None
    performed_by: int | None
    channel: ActivityChannel | None
    duration_minutes: int | None
    activity_source_type: ActivitySourceType | None
    activity_source_id: int | None
    created_at: datetime
    updated_at: datetime