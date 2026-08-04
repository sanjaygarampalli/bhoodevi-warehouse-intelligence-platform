from typing import List, Optional

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[Company]):
    def __init__(self) -> None:
        super().__init__(model=Company)

    def get_by_name(
        self,
        db: Session,
        company_name: str,
    ) -> Optional[Company]:
        stmt = select(self.model).where(
            self.model.company_name == company_name
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_industry(
        self,
        db: Session,
        industry: str,
    ) -> List[Company]:
        stmt = select(self.model).where(
            self.model.industry == industry
        )
        return db.execute(stmt).scalars().all()

    def get_by_city(
        self,
        db: Session,
        city: str,
    ) -> List[Company]:
        stmt = select(self.model).where(
            self.model.headquarters_city == city
        )
        return db.execute(stmt).scalars().all()

    def get_by_business_status(
        self,
        db: Session,
        business_status: str,
    ) -> List[Company]:
        stmt = select(self.model).where(
            self.model.business_status == business_status
        )
        return db.execute(stmt).scalars().all()