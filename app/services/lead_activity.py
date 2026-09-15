from datetime import datetime

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.deal import Deal
from app.models.decision_maker import DecisionMaker
from app.models.lead import Lead
from app.models.lead_activity import LeadActivity
from app.repositories.lead import LeadRepository
from app.repositories.lead_activity import LeadActivityRepository
from app.schemas.lead_activity import (
    LeadActivityCreate,
    LeadActivityUpdate,
)


class LeadActivityConflict(ValueError):
    pass


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

        self._validate_relationships(db, activity.lead_id, activity.deal_id, activity.decision_maker_id)
        db_activity = LeadActivity(
            **activity.model_dump()
        )
        if db_activity.activity_date is None:
            db_activity.activity_date = datetime.utcnow()
        return self.repository.create(db, db_activity)

    def _validate_relationships(self, db, lead_id, deal_id=None, decision_maker_id=None):
        lead = db.get(Lead, lead_id)
        if lead is None:
            return None
        company = db.get(Company, lead.company_id)
        if deal_id is not None:
            deal = db.get(Deal, deal_id)
            if deal is None:
                raise LeadActivityConflict("Deal not found")
            if deal.deal_status != "OPEN":
                raise LeadActivityConflict("Closed Deals cannot receive execution activities")
            if deal.lead_id != lead.id or company is None or deal.organization_id != company.organization_id:
                raise LeadActivityConflict("Deal must belong to the activity Lead and its organization")
        if decision_maker_id is not None:
            decision_maker = db.get(DecisionMaker, decision_maker_id)
            if decision_maker is None:
                raise LeadActivityConflict("DecisionMaker not found")
            if company is None or decision_maker.company_id != company.id:
                raise LeadActivityConflict("DecisionMaker must belong to the Lead Company")
        return lead

    def list_activities_by_deal(self, db: Session, deal_id: int) -> list[LeadActivity]:
        return self.repository.get_by_deal_id(db, deal_id)

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

        self._validate_relationships(
            db,
            update_data.get("lead_id", db_activity.lead_id),
            update_data.get("deal_id", db_activity.deal_id),
            update_data.get("decision_maker_id", db_activity.decision_maker_id),
        )

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