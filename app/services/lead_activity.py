from sqlalchemy.orm import Session

from app.models.lead_activity import LeadActivity
from app.repositories.lead import LeadRepository
from app.repositories.lead_activity import LeadActivityRepository
from app.schemas.lead_activity import (
    LeadActivityCreate,
    LeadActivityUpdate,
)


class LeadActivityService:
    def __init__(self) -> None:
        self.repository = LeadActivityRepository()
        self.lead_repository = LeadRepository()

    def create_lead_activity(
        self,
        db: Session,
        activity: LeadActivityCreate,
    ) -> LeadActivity | None:
        lead = self.lead_repository.get_by_id(
            db,
            activity.lead_id,
        )

        if lead is None:
            return None

        db_activity = LeadActivity(
            **activity.model_dump()
        )
        return self.repository.create(db, db_activity)

    def get_lead_activity_by_id(
        self,
        db: Session,
        activity_id: int,
    ) -> LeadActivity | None:
        return self.repository.get_by_id(db, activity_id)

    def list_activities_by_lead(
        self,
        db: Session,
        lead_id: int,
    ) -> list[LeadActivity]:
        return self.repository.get_by_lead_id(db, lead_id)

    def update_lead_activity(
        self,
        db: Session,
        activity_id: int,
        activity: LeadActivityUpdate,
    ) -> LeadActivity | None:
        db_activity = self.repository.get_by_id(
            db,
            activity_id,
        )

        if db_activity is None:
            return None

        update_data = activity.model_dump(exclude_unset=True)

        if "lead_id" in update_data and update_data["lead_id"] != db_activity.lead_id:
            lead = self.lead_repository.get_by_id(
                db,
                update_data["lead_id"],
            )

            if lead is None:
                return None

        for key, value in update_data.items():
            setattr(db_activity, key, value)

        return self.repository.update(
            db,
            db_activity,
        )

    def delete_lead_activity(
        self,
        db: Session,
        activity_id: int,
    ) -> LeadActivity | None:
        db_activity = self.repository.get_by_id(
            db,
            activity_id,
        )

        if db_activity is None:
            return None

        self.repository.delete(
            db,
            db_activity,
        )

        return db_activity