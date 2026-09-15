from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.requirement_candidate_conversion import RequirementCandidateConversion


class RequirementCandidateConversionRepository:
    def get_by_candidate(self, db: Session, candidate_id: int, *, lock: bool = False):
        stmt = select(RequirementCandidateConversion).where(
            RequirementCandidateConversion.requirement_candidate_id == candidate_id,
        ).options(
            joinedload(RequirementCandidateConversion.company),
            joinedload(RequirementCandidateConversion.lead),
            joinedload(RequirementCandidateConversion.requirement),
        )
        if lock:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        return db.scalar(stmt)

    def create_pending(self, db: Session, conversion):
        db.add(conversion)
        db.flush()
        return conversion