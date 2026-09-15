import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QualificationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUALIFIED = "QUALIFIED"
    NOT_QUALIFIED = "NOT_QUALIFIED"


class QualificationRecommendation(str, enum.Enum):
    CONTINUE_RESEARCH = "CONTINUE_RESEARCH"
    FOLLOW_UP = "FOLLOW_UP"
    CONTACT_ANOTHER_STAKEHOLDER = "CONTACT_ANOTHER_STAKEHOLDER"
    COLLECT_REQUIREMENT_DETAILS = "COLLECT_REQUIREMENT_DETAILS"
    REVIEW_EXISTING_LEAD = "REVIEW_EXISTING_LEAD"
    CONSIDER_EXPLICIT_LEAD_CREATION = "CONSIDER_EXPLICIT_LEAD_CREATION"
    NO_COMMERCIAL_ACTION = "NO_COMMERCIAL_ACTION"


def _json_type():
    return JSON().with_variant(JSONB(), "postgresql")


class ResponseQualificationAssessment(Base):
    __tablename__ = "response_qualification_assessments"
    __table_args__ = (
        Index("ix_response_qualification_org_company", "organization_id", "company_id"),
        Index("ix_response_qualification_outreach", "outreach_activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[int] = mapped_column(ForeignKey("company_contacts.id", ondelete="CASCADE"), nullable=False)
    outreach_activity_id: Mapped[int] = mapped_column(ForeignKey("contact_outreach_activities.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[QualificationStatus] = mapped_column(String(30), nullable=False, default=QualificationStatus.DRAFT.value)
    observed_facts: Mapped[list[dict[str, Any]]] = mapped_column(_json_type(), nullable=False, default=list)
    commercial_inference: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[QualificationRecommendation] = mapped_column(String(50), nullable=False)
    uncertainty: Mapped[list[str]] = mapped_column(_json_type(), nullable=False, default=list)
    warehouse_details: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False, default=dict)
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    human_review_required: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)