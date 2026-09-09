from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.organization import OrgType, OrganizationStatus, SubscriptionTier
from app.schemas.industry import IndustryResponse


class OrganizationBase(BaseModel):
    org_code: str = Field(..., min_length=1, max_length=20)
    legal_name: str = Field(..., min_length=1, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    org_type: OrgType
    industry_id: Optional[int] = Field(None, gt=0)
    gstin: Optional[str] = Field(None, min_length=1, max_length=15)
    pan: Optional[str] = Field(None, min_length=1, max_length=10)
    website: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: str = Field("India", min_length=1, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    subscription_tier: SubscriptionTier
    status: OrganizationStatus
    settings: Optional[dict[str, Any]] = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    org_code: Optional[str] = Field(None, min_length=1, max_length=20)
    legal_name: Optional[str] = Field(None, min_length=1, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    org_type: Optional[OrgType] = None
    industry_id: Optional[int] = Field(None, gt=0)
    gstin: Optional[str] = Field(None, min_length=1, max_length=15)
    pan: Optional[str] = Field(None, min_length=1, max_length=10)
    website: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=30)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    subscription_tier: Optional[SubscriptionTier] = None
    status: Optional[OrganizationStatus] = None
    settings: Optional[dict[str, Any]] = None

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator(
        "org_code", "legal_name", "org_type", "country", "subscription_tier", "status"
    )
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class OrganizationResponse(OrganizationBase):
    id: int
    public_id: str
    created_at: datetime
    updated_at: datetime
    industry: Optional[IndustryResponse] = None

    model_config = ConfigDict(from_attributes=True)