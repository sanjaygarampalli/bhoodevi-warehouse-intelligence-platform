import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InvestigationStatus(str, enum.Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    UNDER_RESEARCH = "UNDER_RESEARCH"
    VERIFIED = "VERIFIED"
    NEEDS_MORE_RESEARCH = "NEEDS_MORE_RESEARCH"
    NOT_RELEVANT = "NOT_RELEVANT"


class ContactOutreachMethod(str, enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    LINKEDIN = "LINKEDIN"
    WHATSAPP = "WHATSAPP"
    IN_PERSON = "IN_PERSON"
    OTHER = "OTHER"


class OutreachOutcome(str, enum.Enum):
    NO_RESPONSE = "NO_RESPONSE"
    CONTACTED = "CONTACTED"
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    WRONG_CONTACT = "WRONG_CONTACT"
    INVALID_CONTACT = "INVALID_CONTACT"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    OTHER = "OTHER"


class ContactInvestigation(Base):
    __tablename__ = "contact_investigations"
    __table_args__ = (
        Index("ix_contact_investigations_org_company_contact", "organization_id", "company_id", "contact_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[int] = mapped_column(ForeignKey("company_contacts.id", ondelete="CASCADE"), nullable=False, unique=True)
    investigated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    investigation_status: Mapped[InvestigationStatus] = mapped_column(String(30), nullable=False, default=InvestigationStatus.NOT_REVIEWED.value)
    designation_verified: Mapped[bool | None] = mapped_column()
    department_verified: Mapped[bool | None] = mapped_column()
    seniority_verified: Mapped[bool | None] = mapped_column()
    email_verified: Mapped[bool | None] = mapped_column()
    phone_verified: Mapped[bool | None] = mapped_column()
    linkedin_verified: Mapped[bool | None] = mapped_column()
    still_employed: Mapped[bool | None] = mapped_column()
    relevant_to_warehouse_decisions: Mapped[bool | None] = mapped_column()
    potential_decision_maker: Mapped[bool | None] = mapped_column()
    research_notes: Mapped[str | None] = mapped_column(Text)
    selected_for_outreach: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ContactOutreachActivity(Base):
    __tablename__ = "contact_outreach_activities"
    __table_args__ = (
        Index("ix_contact_outreach_org_company_contact_time", "organization_id", "company_id", "contact_id", "performed_at", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[int] = mapped_column(ForeignKey("company_contacts.id", ondelete="CASCADE"), nullable=False)
    performed_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    method: Mapped[ContactOutreachMethod] = mapped_column(String(20), nullable=False)
    performed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[OutreachOutcome | None] = mapped_column(String(30))
    response_status: Mapped[str | None] = mapped_column(String(50))
    next_action: Mapped[str | None] = mapped_column(Text)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)