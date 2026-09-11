from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.organization_membership import MembershipStatus, OrganizationMemberRole


class OrganizationMembershipCreate(BaseModel):
    user_id: int = Field(..., gt=0)
    role: OrganizationMemberRole = OrganizationMemberRole.MEMBER

    model_config = ConfigDict(extra="forbid")


class OrganizationMembershipUpdate(BaseModel):
    role: OrganizationMemberRole | None = None
    status: MembershipStatus | None = None

    model_config = ConfigDict(extra="forbid")


class OrganizationMembershipResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    role: OrganizationMemberRole
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)