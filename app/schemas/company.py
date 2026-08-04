from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CompanyBase(BaseModel):
    company_name: str = Field(..., max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    industry: str = Field(..., max_length=100)
    company_type: str = Field(..., max_length=100)
    products: Optional[str] = None
    website: Optional[str] = Field(None, max_length=255)

    headquarters_city: Optional[str] = Field(None, max_length=100)
    headquarters_state: Optional[str] = Field(None, max_length=100)
    headquarters_country: Optional[str] = Field(
        default="India",
        max_length=100,
    )

    business_status: Optional[str] = Field(
        default="Active",
        max_length=50,
    )

    priority: Optional[str] = Field(
        default="MEDIUM",
        max_length=20,
    )

    data_source: Optional[str] = Field(
        None,
        max_length=100,
    )

    notes: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    company_name: Optional[str] = Field(None, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=100)
    company_type: Optional[str] = Field(None, max_length=100)
    products: Optional[str] = None
    website: Optional[str] = Field(None, max_length=255)

    headquarters_city: Optional[str] = Field(None, max_length=100)
    headquarters_state: Optional[str] = Field(None, max_length=100)
    headquarters_country: Optional[str] = Field(None, max_length=100)

    business_status: Optional[str] = Field(
        None,
        max_length=50,
    )

    priority: Optional[str] = Field(
        None,
        max_length=20,
    )

    data_source: Optional[str] = Field(
        None,
        max_length=100,
    )

    notes: Optional[str] = None


class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyListResponse(BaseModel):
    companies: List[CompanyResponse]

    model_config = ConfigDict(from_attributes=True)