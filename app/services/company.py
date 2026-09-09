from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.services.deal_workflow import protect_deal_reference
from app.services.follow_up_workflow import protect_task_reference

from app.models.company import Company
from app.repositories.company import CompanyRepository
from app.repositories.organization import OrganizationRepository
from app.schemas.company import CompanyCreate, CompanyUpdate


class CompanyService:
    def __init__(self) -> None:
        self.repository = CompanyRepository()
        self.organization_repository = OrganizationRepository()

    def create_company(
        self,
        db: Session,
        company: CompanyCreate,
    ) -> Company:
        if self.organization_repository.get_by_id(db, company.organization_id) is None:
            raise LookupError("Organization not found")
        db_company = Company(**company.model_dump())
        try:
            return self.repository.create(db, db_company)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Company conflicts with existing data") from exc

    def get_company_by_id(
        self,
        db: Session,
        company_id: int,
    ) -> Company | None:
        return self.repository.get_by_id(db, company_id)

    def get_company_by_name(
        self,
        db: Session,
        company_name: str,
    ) -> Company | None:
        return self.repository.get_by_name(db, company_name)

    def list_companies(
        self,
        db: Session,
    ) -> list[Company]:
        return self.repository.get_multi(db)

    def list_companies_by_industry(
        self,
        db: Session,
        industry: str,
    ) -> list[Company]:
        return self.repository.get_by_industry(db, industry)

    def list_companies_by_city(
        self,
        db: Session,
        city: str,
    ) -> list[Company]:
        return self.repository.get_by_city(db, city)

    def list_companies_by_business_status(
        self,
        db: Session,
        business_status: str,
    ) -> list[Company]:
        return self.repository.get_by_business_status(
            db,
            business_status,
        )

    def update_company(
        self,
        db: Session,
        company_id: int,
        company: CompanyUpdate,
    ) -> Company | None:
        db_company = self.repository.get_by_id(
            db,
            company_id,
        )

        if db_company is None:
            return None

        update_data = company.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(db_company, key, value)

        return self.repository.update(
            db,
            db_company,
        )

    def delete_company(
        self,
        db: Session,
        company_id: int,
    ) -> Company | None:
        db_company = self.repository.get_by_id(
            db,
            company_id,
        )

        if db_company is None:
            return None

        protect_deal_reference(db, "company", company_id)
        protect_task_reference(db, "company", company_id)
        self.repository.delete(
            db,
            db_company,
        )

        return db_company