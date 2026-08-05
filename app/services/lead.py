from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.repositories.company import CompanyRepository
from app.repositories.decision_maker import DecisionMakerRepository
from app.repositories.lead import LeadRepository
from app.schemas.lead import (
    LeadCreate,
    LeadUpdate,
)


class LeadService:
    def __init__(self) -> None:
        self.repository = LeadRepository()
        self.company_repository = CompanyRepository()
        self.decision_maker_repository = DecisionMakerRepository()

    def create_lead(
        self,
        db: Session,
        lead: LeadCreate,
    ) -> Lead | None:
        company = self.company_repository.get_by_id(
            db,
            lead.company_id,
        )

        if company is None:
            return None

        if lead.primary_decision_maker_id is not None:
            decision_maker = (
                self.decision_maker_repository.get_by_id(
                    db,
                    lead.primary_decision_maker_id,
                )
            )

            if decision_maker is None:
                return None

        db_lead = Lead(
            **lead.model_dump()
        )
        return self.repository.create(db, db_lead)

    def get_lead_by_id(
        self,
        db: Session,
        lead_id: int,
    ) -> Lead | None:
        return self.repository.get_by_id(db, lead_id)

    def list_leads_by_company(
        self,
        db: Session,
        company_id: int,
    ) -> list[Lead]:
        return self.repository.get_by_company_id(db, company_id)

    def update_lead(
        self,
        db: Session,
        lead_id: int,
        lead: LeadUpdate,
    ) -> Lead | None:
        db_lead = self.repository.get_by_id(
            db,
            lead_id,
        )

        if db_lead is None:
            return None

        update_data = lead.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_lead, key, value)

        return self.repository.update(
            db,
            db_lead,
        )

    def delete_lead(
        self,
        db: Session,
        lead_id: int,
    ) -> Lead | None:
        db_lead = self.repository.get_by_id(
            db,
            lead_id,
        )

        if db_lead is None:
            return None

        self.repository.delete(
            db,
            db_lead,
        )

        return db_lead