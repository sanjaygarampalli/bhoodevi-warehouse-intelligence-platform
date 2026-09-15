from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompanyWarehouseRequirementProfile(Base):
    __tablename__ = "company_warehouse_requirement_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "company_id", name="uq_company_warehouse_requirement_profile_org_company"),
        Index("ix_company_warehouse_requirement_profiles__organization_id", "organization_id"),
        Index("ix_company_warehouse_requirement_profiles__company_id", "company_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    requirements: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())