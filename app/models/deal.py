from datetime import date, datetime
from decimal import Decimal

import enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.deal_pipeline_stage import DealPipelineStage
    from app.models.deal_stage_history import DealStageHistory
    from app.models.lead import Lead
    from app.models.organization import Organization
    from app.models.requirement import Requirement
    from app.models.warehouse_match import WarehouseMatch


class LostReasonCategory(str, enum.Enum):
    PRICE = "PRICE"
    LOCATION = "LOCATION"
    WAREHOUSE_FIT = "WAREHOUSE_FIT"
    AVAILABILITY = "AVAILABILITY"
    TIMING = "TIMING"
    COMPETITOR = "COMPETITOR"
    CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED"
    REQUIREMENT_CHANGED = "REQUIREMENT_CHANGED"
    NO_RESPONSE = "NO_RESPONSE"
    NOT_QUALIFIED = "NOT_QUALIFIED"
    OTHER = "OTHER"


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("deal_status IN ('OPEN','WON','LOST')", name="ck_deals__status"),
        CheckConstraint(
            "(deal_status = 'OPEN' AND closed_at IS NULL) OR "
            "(deal_status IN ('WON','LOST') AND closed_at IS NOT NULL)", name="ck_deals__closure",
        ),
        CheckConstraint("expected_revenue >= 0", name="ck_deals__expected_revenue"),
        Index("ix_deals__stage_id__expected_close_date", "stage_id", "expected_close_date"),
        Index("ix_deals__organization__status", "organization_id", "deal_status"),
        Index("ix_deals__lost_reason_category", "lost_reason_category"),
        Index("uq_deals__open_requirement", "requirement_id", unique=True,
              sqlite_where=text("deal_status = 'OPEN'"), postgresql_where=text("deal_status = 'OPEN'")),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    deal_name: Mapped[str] = mapped_column(String(255))
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id", ondelete="RESTRICT"), index=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="RESTRICT"), index=True)
    selected_warehouse_match_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouse_matches.id", ondelete="RESTRICT"), index=True,
    )
    stage_id: Mapped[int] = mapped_column(ForeignKey("deal_pipeline_stages.id", ondelete="RESTRICT"))
    stage_entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expected_revenue: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    currency: Mapped[str] = mapped_column(String(3), default="INR", server_default="INR")
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    deal_status: Mapped[str] = mapped_column(String(20), default="OPEN", server_default="OPEN")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_reason: Mapped[str | None] = mapped_column(String(255))
    lost_reason_category: Mapped[LostReasonCategory | None] = mapped_column(
        Enum(LostReasonCategory, name="lostreasoncategory"), nullable=True,
    )
    final_commercial_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    final_commercial_currency: Mapped[str | None] = mapped_column(String(3))
    final_lease_duration_months: Mapped[int | None] = mapped_column(Integer)
    outcome_notes: Mapped[str | None] = mapped_column(Text)
    closure_evidence_reference: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lead: Mapped["Lead"] = relationship("Lead")
    requirement: Mapped["Requirement"] = relationship("Requirement")
    selected_warehouse_match: Mapped["WarehouseMatch | None"] = relationship("WarehouseMatch")
    stage: Mapped["DealPipelineStage"] = relationship("DealPipelineStage")
    organization: Mapped["Organization"] = relationship("Organization")
    history: Mapped[list["DealStageHistory"]] = relationship("DealStageHistory", back_populates="deal", passive_deletes="all")