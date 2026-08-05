import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    DISCOVERED = "DISCOVERED"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    POSITIONED = "POSITIONED"
    NEGOTIATING = "NEGOTIATING"
    WON = "WON"
    LOST = "LOST"
    DISQUALIFIED = "DISQUALIFIED"
    DORMANT = "DORMANT"


class LeadSource(str, enum.Enum):
    AI_DISCOVERY = "AI_DISCOVERY"
    LINKEDIN = "LINKEDIN"
    WEBSITE = "WEBSITE"
    IMPORT_EXPORT = "IMPORT_EXPORT"
    GOOGLE_MAPS = "GOOGLE_MAPS"
    TENDER = "TENDER"
    BROKER = "BROKER"
    REFERRAL = "REFERRAL"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


class MoveInTimeframe(str, enum.Enum):
    IMMEDIATE = "IMMEDIATE"
    ONE_TO_THREE_MONTHS = "1_3_MONTHS"
    THREE_TO_SIX_MONTHS = "3_6_MONTHS"
    SIX_TO_TWELVE_MONTHS = "6_12_MONTHS"
    FLEXIBLE = "FLEXIBLE"


class LeadPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("ai_score >= 0 AND ai_score <= 100", name="ck_leads_ai_score_range"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    lead_number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    company_id: Mapped[int] = mapped_column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    status: Mapped[LeadStatus] = mapped_column(Enum(LeadStatus, name="leadstatus"), nullable=False, default=LeadStatus.NEW, index=True)

    lead_source: Mapped[LeadSource] = mapped_column(Enum(LeadSource, name="leadsource"), nullable=False, default=LeadSource.MANUAL)

    space_needed_sqft: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    requirement_type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    target_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    preferred_city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    preferred_state: Mapped[str | None] = mapped_column(String(100), nullable=True)

    preferred_country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    expected_monthly_rent: Mapped[Numeric | None] = mapped_column(Numeric(14, 2), nullable=True)

    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, default="INR")

    move_in_timeframe: Mapped[MoveInTimeframe | None] = mapped_column(Enum(MoveInTimeframe, name="moveintimeframe"), nullable=True)

    lease_tenure_years: Mapped[int | None] = mapped_column(Integer, nullable=True)

    owner_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    primary_decision_maker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("decision_makers.id"), nullable=True, index=True)

    ai_score: Mapped[Numeric | None] = mapped_column(Numeric(5, 2), nullable=True)

    priority: Mapped[LeadPriority] = mapped_column(Enum(LeadPriority, name="leadpriority"), nullable=False, default=LeadPriority.MEDIUM)

    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    disqualified_reason: Mapped[str | None] = mapped_column(String(150), nullable=True)

    closed_reason: Mapped[str | None] = mapped_column(String(150), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (one-directional, read-only)
    company: Mapped["Company"] = relationship("Company")
    primary_decision_maker: Mapped["DecisionMaker | None"] = relationship("DecisionMaker")
    owner_user: Mapped["User | None"] = relationship("User")