from sqlalchemy.orm import Session

from app.models.requirement import Requirement
from app.repositories.lead import LeadRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.requirement import (
    RequirementCreate,
    RequirementUpdate,
)


class RequirementService:
    def __init__(self) -> None:
        self.repository = RequirementRepository()
        self.lead_repository = LeadRepository()

    def create_requirement(
        self,
        db: Session,
        requirement: RequirementCreate,
    ) -> Requirement | None:
        lead = self.lead_repository.get_by_id(
            db,
            requirement.lead_id,
        )

        if lead is None:
            return None

        db_requirement = Requirement(
            **requirement.model_dump()
        )
        return self.repository.create(db, db_requirement)

    def get_requirement_by_id(
        self,
        db: Session,
        requirement_id: int,
    ) -> Requirement | None:
        return self.repository.get_by_id(db, requirement_id)

    def list_requirements_by_lead(
        self,
        db: Session,
        lead_id: int,
    ) -> list[Requirement]:
        return self.repository.get_by_lead_id(db, lead_id)

    def update_requirement(
        self,
        db: Session,
        requirement_id: int,
        requirement: RequirementUpdate,
    ) -> Requirement | None:
        db_requirement = self.repository.get_by_id(
            db,
            requirement_id,
        )

        if db_requirement is None:
            return None

        update_data = requirement.model_dump(exclude_unset=True)

        if "lead_id" in update_data and update_data["lead_id"] != db_requirement.lead_id:
            lead = self.lead_repository.get_by_id(
                db,
                update_data["lead_id"],
            )

            if lead is None:
                return None

        for key, value in update_data.items():
            setattr(db_requirement, key, value)

        return self.repository.update(
            db,
            db_requirement,
        )

    def delete_requirement(
        self,
        db: Session,
        requirement_id: int,
    ) -> Requirement | None:
        db_requirement = self.repository.get_by_id(
            db,
            requirement_id,
        )

        if db_requirement is None:
            return None

        self.repository.delete(
            db,
            db_requirement,
        )

        return db_requirement