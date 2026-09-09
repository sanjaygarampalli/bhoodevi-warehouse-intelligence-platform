from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.lead_score_snapshot import LeadScoreSnapshot


class LeadScoreSnapshotRepository:
    """Append/read only: snapshots have no update API."""

    def create(self, db: Session, snapshot: LeadScoreSnapshot) -> LeadScoreSnapshot:
        try:
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
        except SQLAlchemyError:
            db.rollback()
            raise
        return snapshot

    def get_by_lead_id(
        self, db: Session, lead_id: int, *, limit: int = 100, offset: int = 0,
    ) -> list[LeadScoreSnapshot]:
        stmt = (
            select(LeadScoreSnapshot)
            .where(LeadScoreSnapshot.lead_id == lead_id)
            .order_by(LeadScoreSnapshot.calculated_at.desc(), LeadScoreSnapshot.id.desc())
            .limit(limit).offset(offset)
        )
        return list(db.scalars(stmt).all())