from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DealStageHistory(Base):
    __tablename__ = "deal_stage_history"
    __table_args__ = (
        Index("ix_deal_stage_history__deal_id__changed_at", "deal_id", "changed_at", "id"),
        CheckConstraint("from_stage_id IS NULL OR from_stage_id <> to_stage_id", name="ck_deal_stage_history__different_stages"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="RESTRICT"))
    from_stage_id: Mapped[int | None] = mapped_column(ForeignKey("deal_pipeline_stages.id", ondelete="RESTRICT"), index=True)
    to_stage_id: Mapped[int] = mapped_column(ForeignKey("deal_pipeline_stages.id", ondelete="RESTRICT"), index=True)
    # Display snapshots preserve what the actor saw even after a stage is renamed.
    from_stage_key: Mapped[str | None] = mapped_column(String(50))
    from_stage_name: Mapped[str | None] = mapped_column(String(120))
    to_stage_key: Mapped[str] = mapped_column(String(50))
    to_stage_name: Mapped[str] = mapped_column(String(120))
    changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    change_reason: Mapped[str | None] = mapped_column(String(255))

    deal: Mapped["Deal"] = relationship("Deal", back_populates="history")
    from_stage: Mapped["DealPipelineStage | None"] = relationship("DealPipelineStage", foreign_keys=[from_stage_id])
    to_stage: Mapped["DealPipelineStage"] = relationship("DealPipelineStage", foreign_keys=[to_stage_id])
    changed_by_user: Mapped["User | None"] = relationship("User")


@event.listens_for(DealStageHistory, "before_update")
@event.listens_for(DealStageHistory, "before_delete")
def reject_history_mutation(mapper, connection, target):
    raise ValueError("Deal stage history is immutable")