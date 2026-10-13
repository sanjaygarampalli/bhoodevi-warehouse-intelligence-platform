from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

from app.models.organization_membership import MembershipStatus, OrganizationMemberRole


class UserBase(BaseModel):
    full_name: str = Field(..., max_length=100)
    email: EmailStr
    role: Optional[str] = Field(default="user", max_length=50)
    is_active: Optional[bool] = Field(default=True)


class PasswordInput(BaseModel):
    @field_validator("password", check_fields=False)
    @classmethod
    def validate_password_bytes(cls, value):
        if value is not None and (len(value.encode("utf-8")) > 72 or "\x00" in value):
            raise ValueError("Password must be at most 72 UTF-8 bytes and contain no null bytes")
        return value


class UserCreate(UserBase, PasswordInput):
    password: str = Field(..., min_length=8)


class UserUpdate(PasswordInput):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class PasswordChange(PasswordInput):
    model_config = ConfigDict(extra="forbid")
    current_password: str
    password: str = Field(min_length=8)


class SessionRevocation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deactivate: bool = False


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationContext(BaseModel):
    organization_id: int
    public_id: str
    org_code: str
    legal_name: str
    trading_name: Optional[str] = None
    role: OrganizationMemberRole
    status: MembershipStatus


class AuthenticatedUserContext(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: Optional[str] = None
    is_active: bool


class AuthenticatedContextResponse(BaseModel):
    user: AuthenticatedUserContext
    organizations: list[OrganizationContext]


# Backward compatibility - keep existing classes
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Alias for login - kept for backward compatibility
UserLogin = UserCreate


class GoogleLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credential: str = Field(min_length=1, max_length=8192)
    nonce: str = Field(min_length=32, max_length=128)
    link_password: str | None = Field(default=None, max_length=72)
