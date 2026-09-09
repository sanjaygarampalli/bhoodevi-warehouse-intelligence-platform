from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.repositories.industry import IndustryRepository
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    def __init__(self) -> None:
        self.repository = OrganizationRepository()
        self.industry_repository = IndustryRepository()

    def _validate_references(
        self, db: Session, data: dict, organization_id: int | None = None
    ) -> None:
        industry_id = data.get("industry_id")
        if industry_id is not None:
            if self.industry_repository.get_by_id(db, industry_id) is None:
                raise LookupError("Industry not found")

        for field, lookup in (
            ("org_code", self.repository.get_by_org_code),
            ("gstin", self.repository.get_by_gstin),
            ("pan", self.repository.get_by_pan),
        ):
            if data.get(field) is not None:
                existing = lookup(db, data[field])
                if existing is not None and existing.id != organization_id:
                    raise ValueError(f"Organization {field} already exists")

    def create_organization(
        self, db: Session, organization: OrganizationCreate
    ) -> Organization:
        data = organization.model_dump()
        self._validate_references(db, data)
        db_organization = Organization(public_id=str(uuid4()), **data)
        try:
            return self.repository.create(db, db_organization)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Organization conflicts with existing data") from exc

    def get_organization_by_id(
        self, db: Session, organization_id: int
    ) -> Organization | None:
        return self.repository.get_by_id(db, organization_id)

    def list_organizations(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> list[Organization]:
        return self.repository.get_multi(db, skip=skip, limit=limit)

    def get_organization_by_public_id(
        self, db: Session, public_id: str
    ) -> Organization | None:
        return self.repository.get_by_public_id(db, public_id)

    def get_organization_by_org_code(
        self, db: Session, org_code: str
    ) -> Organization | None:
        return self.repository.get_by_org_code(db, org_code)

    def update_organization(
        self, db: Session, organization_id: int, organization: OrganizationUpdate
    ) -> Organization | None:
        db_organization = self.repository.get_by_id(db, organization_id)
        if db_organization is None:
            return None

        data = organization.model_dump(exclude_unset=True)
        self._validate_references(db, data, organization_id)
        for key, value in data.items():
            setattr(db_organization, key, value)
        try:
            return self.repository.update(db, db_organization)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Organization conflicts with existing data") from exc

    def delete_organization(
        self, db: Session, organization_id: int
    ) -> Organization | None:
        db_organization = self.repository.get_by_id(db, organization_id)
        if db_organization is None:
            return None
        if self.repository.has_companies(db, organization_id):
            raise ValueError("Organization has companies and cannot be deleted")
        try:
            self.repository.delete(db, db_organization)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Organization is referenced by existing data") from exc
        return db_organization