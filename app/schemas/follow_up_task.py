from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.models.follow_up_task import TaskStatus, TaskType, as_utc
from app.models.lead import LeadPriority


class TaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class NextActionTaskCreate(TaskInput):
    due_at: AwareDatetime
    assigned_to_user_id: int | None = Field(None, gt=0)

    @field_validator("due_at")
    @classmethod
    def normalize_due(cls, value):
        return as_utc(value)


class FollowUpTaskCreate(NextActionTaskCreate):
    lead_id: int = Field(gt=0)
    deal_id: int | None = Field(None, gt=0)
    subject: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    task_type: TaskType = TaskType.OTHER
    priority: LeadPriority = LeadPriority.MEDIUM


class FollowUpTaskUpdate(TaskInput):
    """Lead/Deal identity, recommendation context and closure are not generic edits."""
    subject: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=10000)
    task_type: TaskType | None = None
    priority: LeadPriority | None = None
    assigned_to_user_id: int | None = Field(None, gt=0)
    due_at: AwareDatetime | None = None
    status: Literal["OPEN", "IN_PROGRESS"] | None = None

    @field_validator("subject", "task_type", "priority", "due_at", "status")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return as_utc(value) if isinstance(value, datetime) else value


class TaskCompletion(TaskInput):
    completion_notes: str | None = Field(None, max_length=10000)


class TaskCancellation(TaskInput):
    cancellation_reason: str | None = Field(None, max_length=10000)


class FollowUpTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: int
    deal_id: int | None
    assigned_to_user_id: int | None
    subject: str
    description: str | None
    task_type: TaskType
    priority: LeadPriority
    status: TaskStatus
    due_at: datetime
    completed_at: datetime | None
    cancelled_at: datetime | None
    completion_notes: str | None
    cancellation_reason: str | None
    recommendation_key: str | None
    recommendation_context: dict | None
    created_at: datetime
    updated_at: datetime
    is_overdue: bool = False

    @field_validator("due_at", "completed_at", "cancelled_at", "created_at", "updated_at", mode="before")
    @classmethod
    def normalize_timestamps(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return as_utc(value)