from sqlalchemy.orm import Session

from app.models.decision_maker import DecisionMaker
from app.repositories.company import CompanyRepository
from app.repositories.decision_maker import DecisionMakerRepository
from app.schemas.decision_maker import (
    DecisionMakerCreate,
    DecisionMakerUpdate,
)


class DecisionMakerService:
    def __init__(self) -> None:
        self.repository = DecisionMakerRepository()
        self.company_repository = CompanyRepository()

    def create_decision_maker(
        self,
        db: Session,
        decision_maker: DecisionMakerCreate,
    ) -> DecisionMaker:
        company = self.company_repository.get_by_id(
            db,
            decision_maker.company_id,
        )

        if company is None:
            return None

        db_decision_maker = DecisionMaker(
            **decision_maker.model_dump()
        )
        return self.repository.create(db, db_decision_maker)

    def get_decision_maker_by_id(
        self,
        db: Session,
        decision_maker_id: int,
    ) -> DecisionMaker | None:
        return self.repository.get_by_id(db, decision_maker_id)

    def list_decision_makers_by_company(
        self,
        db: Session,
        company_id: int,
    ) -> list[DecisionMaker]:
        return self.repository.get_by_company_id(db, company_id)

    def update_decision_maker(
        self,
        db: Session,
        decision_maker_id: int,
        decision_maker: DecisionMakerUpdate,
    ) -> DecisionMaker | None:
        db_decision_maker = self.repository.get_by_id(
            db,
            decision_maker_id,
        )

        if db_decision_maker is None:
            return None

        update_data = decision_maker.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_decision_maker, key, value)

        return self.repository.update(
            db,
            db_decision_maker,
        )

    def delete_decision_maker(
        self,
        db: Session,
        decision_maker_id: int,
    ) -> DecisionMaker | None:
        db_decision_maker = self.repository.get_by_id(
            db,
            decision_maker_id,
        )

        if db_decision_maker is None:
            return None

        self.repository.delete(
            db,
            db_decision_maker,
        )

        return db_decision_maker