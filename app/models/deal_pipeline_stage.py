from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.organization import Organization


class DealPipelineStage(Base):
    __tablename__ = "deal_pipeline_stages"
    __table_args__ = (
        UniqueConstraint("organization_id", "stage_key", name="uq_deal_pipeline_stages__organization__key"),
        UniqueConstraint("organization_id", "stage_order", name="uq_deal_pipeline_stages__organization__order"),
        CheckConstraint("stage_order >= 0", name="ck_deal_pipeline_stages__order"),
        CheckConstraint(
            "(is_terminal AND ((is_won AND NOT is_lost) OR (is_lost AND NOT is_won))) "
            "OR (NOT is_terminal AND NOT is_won AND NOT is_lost)",
            name="ck_deal_pipeline_stages__terminal",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"), index=True)
    stage_name: Mapped[str] = mapped_column(String(120))
    stage_key: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    stage_order: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_won: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    is_lost: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    organization: Mapped["Organization"] = relationship("Organization")