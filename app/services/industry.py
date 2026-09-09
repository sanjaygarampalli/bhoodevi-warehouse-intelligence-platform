from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.industry import Industry
from app.repositories.industry import IndustryRepository
from app.schemas.industry import IndustryCreate, IndustryUpdate


class IndustryService:
    def __init__(self) -> None:
        self.repository = IndustryRepository()

    def _check_duplicates(
        self, db: Session, data: dict, industry_id: int | None = None
    ) -> None:
        for field, lookup in (
            ("code", self.repository.get_by_code),
            ("name", self.repository.get_by_name),
        ):
            if field in data:
                existing = lookup(db, data[field])
                if existing is not None and existing.id != industry_id:
                    raise ValueError(f"Industry {field} already exists")

    def create_industry(self, db: Session, industry: IndustryCreate) -> Industry:
        data = industry.model_dump()
        self._check_duplicates(db, data)
        try:
            return self.repository.create(db, Industry(**data))
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Industry conflicts with existing data") from exc

    def get_industry_by_id(self, db: Session, industry_id: int) -> Industry | None:
        return self.repository.get_by_id(db, industry_id)

    def get_industry_by_code(self, db: Session, code: str) -> Industry | None:
        return self.repository.get_by_code(db, code)

    def list_industries(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> list[Industry]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def update_industry(
        self, db: Session, industry_id: int, industry: IndustryUpdate
    ) -> Industry | None:
        db_industry = self.repository.get_by_id(db, industry_id)
        if db_industry is None:
            return None

        data = industry.model_dump(exclude_unset=True)
        self._check_duplicates(db, data, industry_id)
        for key, value in data.items():
            setattr(db_industry, key, value)
        try:
            return self.repository.update(db, db_industry)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Industry conflicts with existing data") from exc

    def delete_industry(self, db: Session, industry_id: int) -> Industry | None:
        db_industry = self.repository.get_by_id(db, industry_id)
        if db_industry is None:
            return None
        try:
            self.repository.delete(db, db_industry)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Industry is referenced by existing data") from exc
        return db_industry