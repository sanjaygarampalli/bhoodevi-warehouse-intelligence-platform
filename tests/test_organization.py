"""Unit tests for the Organization domain."""
import uuid
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes import router
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import Company, Industry, Organization, OrgType, OrganizationStatus
from app.models.user import User
from app.repositories.organization import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.organization import OrganizationService

# Check if SubscriptionTier exists
try:
    from app.models import SubscriptionTier
    HAS_SUBSCRIPTION_TIER = True
except ImportError:
    HAS_SUBSCRIPTION_TIER = False


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database for each test."""
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    # Enable foreign key constraints for SQLite (required for ON DELETE behavior)
    session.execute(text("PRAGMA foreign_keys = ON"))
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def industry(db_session):
    """Create a test industry."""
    industry = Industry(
        code="TECH",
        name="Technology",
        category="Information Technology",
        description="Software and IT services",
        is_active=True,
    )
    db_session.add(industry)
    db_session.commit()
    db_session.refresh(industry)
    return industry


@pytest.fixture(scope="function")
def organization(db_session, industry):
    """Create a test organization."""
    org = Organization(
        public_id=str(uuid.uuid4()),
        org_code="ORG-001",
        legal_name="Test Organization Pvt. Ltd.",
        trading_name="Test Org",
        org_type=OrgType.PVT_LTD,
        industry_id=industry.id,
        gstin="27AAAAA0000A1Z5",
        pan="AAAAA0000A",
        website="https://example.com",
        email="contact@example.com",
        phone="+91-9876543210",
        address_line1="123 Test Street",
        address_line2="Suite 100",
        city="Test City",
        state="Maharashtra",
        country="India",
        postal_code="400001",
        subscription_tier="GROWTH" if not HAS_SUBSCRIPTION_TIER else None,
        status=OrganizationStatus.ACTIVE,
    )
    if HAS_SUBSCRIPTION_TIER:
        from app.models import SubscriptionTier
        org.subscription_tier = SubscriptionTier.GROWTH

    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org
 
# ====================
# Model Tests
# ====================
class TestOrganizationModel:
    """Tests for Organization SQLAlchemy model."""

    def test_create_organization_minimal(self, db_session):
        """Test creating organization with only required fields."""
        org = Organization(
            public_id=str(uuid.uuid4()),
            org_code="ORG-MIN",
            legal_name="Minimal Organization",
            org_type=OrgType.PVT_LTD,
            country="India",
            subscription_tier=SubscriptionTier.FREE,
            status=OrganizationStatus.ACTIVE,
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        assert org.id is not None
        assert org.org_code == "ORG-MIN"
        assert org.legal_name == "Minimal Organization"
        assert org.org_type == OrgType.PVT_LTD
        assert org.country == "India"
        assert org.status in OrganizationStatus
        assert org.created_at is not None

    def test_create_organization_with_industry(self, db_session, industry):
        """Test creating organization linked to industry."""
        org = Organization(
            public_id=str(uuid.uuid4()),
            org_code="ORG-IND",
            legal_name="Organization with Industry",
            org_type=OrgType.LLP,
            industry_id=industry.id,
            country="India",
            subscription_tier=SubscriptionTier.FREE,
            status=OrganizationStatus.ACTIVE,
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        assert org.industry is not None
        assert org.industry.id == industry.id
        assert org.industry.name == "Technology"

    def test_organization_without_industry(self, db_session):
        """Test creating organization without industry (nullable)."""
        org = Organization(
            public_id=str(uuid.uuid4()),
            org_code="ORG-NOIND",
            legal_name="Organization without Industry",
            org_type=OrgType.SOLE_PROPRIETOR,
            country="India",
            subscription_tier=SubscriptionTier.FREE,
            status=OrganizationStatus.ACTIVE,
        )
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        assert org.industry_id is None
        assert org.industry is None

    def test_organization_unique_constraints(self, db_session, organization):
        """Test unique constraints on public_id and org_code."""
        # Try to create another org with same org_code
        from app.models import OrganizationStatus, SubscriptionTier

        org2 = Organization(
            public_id=str(uuid.uuid4()),
            org_code="ORG-001",  # Same as fixture
            legal_name="Duplicate Org Code",
            org_type=OrgType.PVT_LTD,
            status=OrganizationStatus.ACTIVE,
        )
        if HAS_SUBSCRIPTION_TIER:
            org2.subscription_tier = SubscriptionTier.FREE
        db_session.add(org2)
        with pytest.raises(Exception):  # IntegrityError on unique constraint
            db_session.commit()

class TestIndustryModel:
    """Tests for Industry SQLAlchemy model."""

    def test_create_industry(self, db_session):
        """Test creating a new industry."""
        industry = Industry(
            code="MFG",
            name="Manufacturing",
            category="Industrial",
            description="Industrial manufacturing",
        )
        db_session.add(industry)
        db_session.commit()
        db_session.refresh(industry)

        assert industry.id is not None
        assert industry.code == "MFG"
        assert industry.name == "Manufacturing"
        assert industry.category == "Industrial"
        assert industry.is_active is True

    def test_industry_unique_code(self, db_session):
        """Test that industry code is unique."""
        industry1 = Industry(code="TEST", name="Test Industry 1")
        industry2 = Industry(code="TEST", name="Test Industry 2")

        db_session.add(industry1)
        db_session.commit()

        db_session.add(industry2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_industry_unique_name(self, db_session):
        """Test that industry name is unique."""
        industry1 = Industry(code="TEST1", name="Unique Industry")
        industry2 = Industry(code="TEST2", name="Unique Industry")

        db_session.add(industry1)
        db_session.commit()

        db_session.add(industry2)
        with pytest.raises(Exception):
            db_session.commit()


# ====================
# Relationship Tests
# ====================
class TestOrganizationIndustryRelationship:
    """Tests for Organization-Industry relationship."""

    def test_get_industry_via_relationship(self, db_session, organization):
        """Test that industry can be accessed via organization.industry."""
        assert organization.industry is not None
        assert organization.industry.code == "TECH"

    def test_cascade_on_industry_delete(self, db_session, organization):
        """Test that deleting industry does not cascade to organization."""
        industry_id = organization.industry.id

        db_session.delete(organization.industry)
        db_session.commit()

        # Organization should still exist but without industry
        org = db_session.query(Organization).filter_by(id=organization.id).first()
        assert org is not None
        assert org.industry_id is None


# ====================
# Enum Tests
# ====================
class TestOrganizationEnums:
    """Tests for Organization enum types."""

    def test_org_type_enum_values(self):
        """Test all OrgType enum values exist."""
        assert OrgType.SOLE_PROPRIETOR == "SOLE_PROPRIETOR"
        assert OrgType.PARTNERSHIP == "PARTNERSHIP"
        assert OrgType.LLP == "LLP"
        assert OrgType.PVT_LTD == "PVT_LTD"
        assert OrgType.PUBLIC_LTD == "PUBLIC_LTD"
        assert OrgType.GOVT == "GOVT"
        assert OrgType.OTHER == "OTHER"

    def test_organization_status_enum_values(self):
        """Test all OrganizationStatus enum values exist."""
        assert OrganizationStatus.TRIAL == "TRIAL"
        assert OrganizationStatus.ACTIVE == "ACTIVE"
        assert OrganizationStatus.SUSPENDED == "SUSPENDED"
        assert OrganizationStatus.CANCELLED == "CANCELLED"

    def test_subscription_tier_enum_values(self):
        """Test all SubscriptionTier enum values exist if importable."""
        if HAS_SUBSCRIPTION_TIER:
            from app.models import SubscriptionTier
            assert SubscriptionTier.FREE == "FREE"
            assert SubscriptionTier.STARTER == "STARTER"
            assert SubscriptionTier.GROWTH == "GROWTH"
            assert SubscriptionTier.ENTERPRISE == "ENTERPRISE"


# ====================
# Organization <-> Company Tenancy Tests
# ====================
class TestOrganizationCompanyTenancy:
    """Tests for the Organization -> Company tenancy relationship."""

    @pytest.fixture
    def org(self, db_session):
        """Create a test organization (tenant)."""
        organization = Organization(
            public_id=str(uuid.uuid4()),
            org_code="ORG-TENANT",
            legal_name="Tenant Organization Pvt. Ltd.",
            org_type=OrgType.PVT_LTD,
            country="India",
            subscription_tier="GROWTH" if not HAS_SUBSCRIPTION_TIER else None,
            status=OrganizationStatus.ACTIVE,
        )
        if HAS_SUBSCRIPTION_TIER:
            from app.models import SubscriptionTier
            organization.subscription_tier = SubscriptionTier.GROWTH
        db_session.add(organization)
        db_session.commit()
        db_session.refresh(organization)
        return organization

    def test_company_accepts_organization_id(self, db_session, org):
        """Company can be created with a valid organization_id."""
        company = Company(
            organization_id=org.id,
            company_name="Acme Corp",
            industry="Manufacturing",
            company_type="Private",
        )
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)

        assert company.organization_id == org.id
        assert company.id is not None

    def test_company_organization_relationship_loads(self, db_session, org):
        """Organization can access its companies via the back-relationship."""
        company = Company(
            organization_id=org.id,
            company_name="Beta Industries",
            industry="Retail",
            company_type="Private",
        )
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)

        assert company.organization_owners.id == org.id
        assert company.organization_owners.legal_name == org.legal_name

    def test_organization_compiles_back_relationship(self, db_session, org):
        """Organization.companies is a valid relationship attribute."""
        company1 = Company(
            organization_id=org.id,
            company_name="Tenant Co 1",
            industry="IT",
            company_type="Private",
        )
        company2 = Company(
            organization_id=org.id,
            company_name="Tenant Co 2",
            industry="Logistics",
            company_type="Private",
        )
        db_session.add_all([company1, company2])
        db_session.commit()

        db_session.refresh(org)
        assert hasattr(org, "companies")
        assert isinstance(org.companies, list)
        assert len(org.companies) == 2
        names = {c.company_name for c in org.companies}
        assert names == {"Tenant Co 1", "Tenant Co 2"}

    def test_company_organization_id_rejects_invalid_fk(self, db_session):
        """Company with non-existent organization_id should raise IntegrityError."""
        company = Company(
            organization_id=999999,
            company_name="Invalid Tenant Co",
            industry="FMCG",
            company_type="Private",
        )
        db_session.add(company)
        with pytest.raises(Exception):
            db_session.commit()

    def test_company_organization_id_is_required(self, db_session):
        """Company without organization_id should raise an error (NOT NULL)."""
        company = Company(
            company_name="NoTenant Co",
            industry="FMCG",
            company_type="Private",
        )
        db_session.add(company)
        with pytest.raises(Exception):
            db_session.commit()

    def test_existing_company_fields_remain_intact(self, db_session, org):
        """Adding organization_id does not change other Company columns."""
        company = Company(
            organization_id=org.id,
            company_name="Legacy Co",
            legal_name="Legacy Co Pvt. Ltd.",
            industry="Manufacturing",
            company_type="Private",
            products="Widgets",
            website="https://legacy.example.com",
            headquarters_city="Mumbai",
            headquarters_state="Maharashtra",
            headquarters_country="India",
            business_status="Active",
            priority="MEDIUM",
            data_source="manual",
            notes="pre-tenancy fields preserved",
        )
        db_session.add(company)
        db_session.commit()
        db_session.refresh(company)

        assert company.company_name == "Legacy Co"
        assert company.legal_name == "Legacy Co Pvt. Ltd."
        assert company.industry == "Manufacturing"
        assert company.company_type == "Private"
        assert company.products == "Widgets"
        assert company.website == "https://legacy.example.com"
        assert company.headquarters_city == "Mumbai"
        assert company.headquarters_country == "India"
        assert company.business_status == "Active"
        assert company.priority == "MEDIUM"
        assert company.data_source == "manual"
        assert company.notes == "pre-tenancy fields preserved"
        assert company.created_at is not None
        assert company.updated_at is not None


@pytest.fixture()
def organization_payload():
    return {
        "org_code": "ORG-API",
        "legal_name": "API Organization",
        "org_type": "PVT_LTD",
        "subscription_tier": "FREE",
        "status": "TRIAL",
    }


@pytest.fixture()
def client(db_session):
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, full_name="Admin", email="admin@example.com", role="admin"
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestOrganizationSchema:
    @pytest.mark.parametrize("field,value", [
        ("org_code", " "), ("org_code", "X" * 21),
        ("legal_name", "X" * 256), ("email", "invalid-email"),
        ("org_type", "INVALID"), ("subscription_tier", "INVALID"),
        ("status", "INVALID"), ("industry_id", 0),
        ("settings", []), ("gstin", "X" * 16), ("pan", "X" * 11),
        ("public_id", "client-supplied"),
    ])
    def test_invalid_create(self, organization_payload, field, value):
        with pytest.raises(ValidationError):
            OrganizationCreate(**{**organization_payload, field: value})

    @pytest.mark.parametrize("field", [
        "org_code", "legal_name", "org_type", "country", "subscription_tier", "status"
    ])
    def test_update_rejects_null_required_fields(self, field):
        with pytest.raises(ValidationError):
            OrganizationUpdate(**{field: None})

    def test_partial_updates_and_immutable_public_id(self):
        assert OrganizationUpdate().model_dump(exclude_unset=True) == {}
        assert OrganizationUpdate(industry_id=None).model_dump(exclude_unset=True) == {
            "industry_id": None
        }
        with pytest.raises(ValidationError):
            OrganizationUpdate(public_id=str(uuid.uuid4()))


class TestOrganizationService:
    @pytest.mark.parametrize("field,value", [
        ("gstin", "27AAAAA0000A1Z5"), ("pan", "AAAAA0000A")
    ])
    def test_tax_identifier_database_conflicts_roll_back(
        self, db_session, organization_payload, monkeypatch, field, value
    ):
        service = OrganizationService()
        service.create_organization(db_session, OrganizationCreate(**{
            **organization_payload, field: value
        }))
        second = service.create_organization(db_session, OrganizationCreate(**{
            **organization_payload, "org_code": "SECOND"
        }))
        second_id = second.id
        # Bypass the precheck to exercise the unique index and transaction recovery.
        monkeypatch.setattr(service, "_validate_references", lambda *args: None)
        with pytest.raises(ValueError, match="conflicts"):
            service.update_organization(
                db_session, second_id, OrganizationUpdate(**{field: value})
            )
        assert getattr(service.get_organization_by_id(db_session, second_id), field) is None
        assert service.repository.count(db_session) == 2

    def test_identifier_lookups(self, db_session, organization):
        repository = OrganizationRepository()
        service = OrganizationService()
        assert repository.get_by_public_id(db_session, organization.public_id) is organization
        assert repository.get_by_public_id(db_session, str(uuid.uuid4())) is None
        assert service.get_organization_by_public_id(
            db_session, organization.public_id
        ) is organization
        assert service.get_organization_by_org_code(
            db_session, organization.org_code
        ) is organization
        assert service.get_organization_by_public_id(db_session, str(uuid.uuid4())) is None
        assert service.get_organization_by_org_code(db_session, "MISSING") is None

    def test_update_database_conflict_rolls_back(
        self, db_session, organization_payload, monkeypatch
    ):
        service = OrganizationService()
        first = service.create_organization(
            db_session, OrganizationCreate(**organization_payload)
        )
        second = service.create_organization(db_session, OrganizationCreate(**{
            **organization_payload, "org_code": "SECOND"
        }))
        second_id = second.id
        monkeypatch.setattr(service, "_validate_references", lambda *args: None)
        with pytest.raises(ValueError, match="conflicts"):
            service.update_organization(
                db_session, second_id, OrganizationUpdate(org_code=first.org_code)
            )
        assert service.get_organization_by_id(db_session, second_id).org_code == "SECOND"
        assert service.update_organization(
            db_session, second_id, OrganizationUpdate(legal_name="Recovered")
        ).legal_name == "Recovered"

    def test_pagination_is_ordered_by_id(self, db_session, organization_payload):
        for organization_id, code in ((20, "A"), (10, "Z"), (30, "B")):
            db_session.add(Organization(
                **{**organization_payload, "org_code": code},
                id=organization_id, public_id=str(uuid.uuid4()),
            ))
        db_session.commit()
        repository = OrganizationRepository()
        assert [row.id for row in repository.get_multi(db_session)] == [10, 20, 30]
        assert [row.id for row in repository.get_multi(db_session, skip=1, limit=1)] == [20]

    def test_crud_and_repository(self, db_session, industry, organization_payload):
        service = OrganizationService()
        created = service.create_organization(db_session, OrganizationCreate(
            **organization_payload, industry_id=industry.id,
            gstin="27AAAAA0000A1Z5", pan="AAAAA0000A"
        ))
        assert uuid.UUID(created.public_id).version == 4
        assert created.industry is industry
        repository = OrganizationRepository()
        assert repository.get_by_org_code(db_session, created.org_code) is created
        assert repository.get_by_gstin(db_session, created.gstin) is created
        assert repository.get_by_pan(db_session, created.pan) is created
        assert repository.has_companies(db_session, created.id) is False
        assert service.list_organizations(db_session) == [created]
        updated = service.update_organization(
            db_session, created.id, OrganizationUpdate(industry_id=None, status="ACTIVE")
        )
        assert updated.industry_id is None
        assert updated.industry is None
        assert updated.status == OrganizationStatus.ACTIVE
        organization_id = created.id
        assert service.delete_organization(db_session, organization_id) is not None
        assert service.get_organization_by_id(db_session, organization_id) is None

    def test_database_conflict_rolls_back(self, db_session, organization_payload, monkeypatch):
        service = OrganizationService()
        payload = OrganizationCreate(**organization_payload)
        service.create_organization(db_session, payload)
        monkeypatch.setattr(service, "_validate_references", lambda *args: None)
        with pytest.raises(ValueError, match="conflicts"):
            service.create_organization(db_session, payload)
        assert service.repository.count(db_session) == 1
        assert service.create_organization(db_session, OrganizationCreate(
            **{**organization_payload, "org_code": "SECOND"}
        )).id is not None


class TestOrganizationAPI:
    @pytest.mark.parametrize("field,value", [
        ("gstin", "27AAAAA0000A1Z5"), ("pan", "AAAAA0000A")
    ])
    def test_nullable_tax_identifier_can_be_cleared_and_reused(
        self, client, organization_payload, field, value
    ):
        first = client.post("/organizations/", json={
            **organization_payload, field: value
        }).json()
        second = client.post("/organizations/", json={
            **organization_payload, "org_code": "SECOND"
        }).json()
        response = client.put(f"/organizations/{first['id']}", json={field: None})
        assert response.status_code == 200, response.text
        assert response.json()[field] is None
        assert client.get(f"/organizations/{second['id']}").json()[field] is None
        response = client.put(f"/organizations/{second['id']}", json={field: value})
        assert response.status_code == 200, response.text
        assert response.json()[field] == value

    def test_identifier_lookups_and_immutable_public_id(
        self, client, industry, organization_payload
    ):
        response = client.post("/organizations/", json={
            **organization_payload, "industry_id": industry.id
        })
        assert response.status_code == 200, response.text
        created = response.json()
        public_path = f"/organizations/public-id/{created['public_id']}"
        code_path = f"/organizations/code/{created['org_code']}"
        for path in (public_path, code_path):
            response = client.get(path)
            assert response.status_code == 200, response.text
            assert response.json() == created
            assert response.json()["industry"]["code"] == "TECH"
        updated = client.put(f"/organizations/{created['id']}", json={
            "org_code": "RENAMED", "industry_id": None
        })
        assert updated.status_code == 200, updated.text
        assert updated.json()["public_id"] == created["public_id"]
        assert client.get(public_path).json() == updated.json()
        assert client.get(code_path).status_code == 404
        assert client.get("/organizations/code/RENAMED").json() == updated.json()
        assert client.put(f"/organizations/{created['id']}", json={
            "public_id": str(uuid.uuid4())
        }).status_code == 422
        assert client.get(public_path).json() == updated.json()
        assert client.delete(f"/organizations/{created['id']}").status_code == 200
        assert client.get(public_path).status_code == 404
        assert client.get("/organizations/code/RENAMED").status_code == 404

    @pytest.mark.parametrize("path,status", [
        ("/organizations/code/MISSING", 404),
        ("/organizations/public-id/00000000-0000-0000-0000-000000000000", 404),
        ("/organizations/public-id/not-a-uuid", 422),
        (f"/organizations/code/{'X' * 21}", 422),
    ])
    def test_identifier_lookup_errors(self, client, path, status):
        assert client.get(path).status_code == status

    def test_linked_crud_without_orm_fixtures(self, client, organization_payload):
        industries = []
        for code in ("TECH", "MFG"):
            response = client.post("/industries/", json={"code": code, "name": code})
            assert response.status_code == 200, response.text
            industries.append(response.json())
        organizations = []
        for code in ("FIRST", "SECOND"):
            response = client.post("/organizations/", json={
                **organization_payload, "org_code": code,
                "industry_id": industries[0]["id"],
            })
            assert response.status_code == 200, response.text
            organizations.append(response.json())

        first_id = organizations[0]["id"]
        response = client.put(f"/organizations/{first_id}", json={
            "industry_id": industries[1]["id"]
        })
        assert response.status_code == 200, response.text
        assert response.json()["industry"]["code"] == "MFG"
        assert response.json()["public_id"] == organizations[0]["public_id"]
        assert client.delete(f"/industries/{industries[0]['id']}").status_code == 200
        assert client.get(f"/organizations/{organizations[1]['id']}").json()["industry"] is None
        assert client.get(f"/organizations/{first_id}").json()["industry"]["code"] == "MFG"
        for organization in organizations:
            assert client.delete(f"/organizations/{organization['id']}").status_code == 200
        assert client.get("/organizations/").json() == []
        assert client.get(f"/industries/{industries[1]['id']}").status_code == 200

    def test_crud_with_industry(self, client, industry, organization_payload):
        response = client.post("/organizations/", json={
            **organization_payload, "industry_id": industry.id,
            "settings": {"notifications": {"email": True}},
            "email": "contact@example.com",
        })
        assert response.status_code == 200, response.text
        created = response.json()
        organization_id = created["id"]
        public_id = created["public_id"]
        assert uuid.UUID(public_id).version == 4
        assert created["industry"]["id"] == industry.id
        assert created["country"] == "India"
        assert created["created_at"] and created["updated_at"]
        assert created["settings"] == {"notifications": {"email": True}}
        assert client.get(f"/organizations/{organization_id}").status_code == 200
        assert len(client.get("/organizations/").json()) == 1
        updated = client.put(f"/organizations/{organization_id}", json={
            "industry_id": None, "settings": None, "email": None, "status": "ACTIVE"
        })
        assert updated.status_code == 200, updated.text
        assert updated.json()["industry"] is None
        assert updated.json()["settings"] is None
        assert updated.json()["email"] is None
        assert updated.json()["public_id"] == public_id
        assert updated.json()["legal_name"] == organization_payload["legal_name"]
        assert client.delete(f"/organizations/{organization_id}").status_code == 200
        assert client.get(f"/organizations/{organization_id}").status_code == 404

    def test_industry_assignment_and_deletion(self, client, industry, organization_payload):
        created = client.post("/organizations/", json=organization_payload).json()
        assert created["industry_id"] is None
        updated = client.put(f"/organizations/{created['id']}", json={
            "industry_id": industry.id
        })
        assert updated.status_code == 200
        assert updated.json()["industry"]["code"] == "TECH"
        assert client.delete(f"/industries/{industry.id}").status_code == 200
        remaining = client.get(f"/organizations/{created['id']}")
        assert remaining.status_code == 200
        assert remaining.json()["industry_id"] is None
        assert remaining.json()["industry"] is None

    def test_invalid_industry_create_and_update(self, client, organization_payload):
        response = client.post("/organizations/", json={
            **organization_payload, "industry_id": 99999
        })
        assert response.status_code == 404
        assert response.json()["detail"] == "Industry not found"
        created = client.post("/organizations/", json=organization_payload).json()
        response = client.put(f"/organizations/{created['id']}", json={
            "industry_id": 99999, "legal_name": "Should not persist"
        })
        assert response.status_code == 404
        assert client.get(f"/organizations/{created['id']}").json()["legal_name"] == organization_payload["legal_name"]

    @pytest.mark.parametrize("field,value", [
        ("org_code", "ORG-API"), ("gstin", "27AAAAA0000A1Z5"), ("pan", "AAAAA0000A")
    ])
    def test_duplicates_create_and_update(self, client, organization_payload, field, value):
        first_payload = {**organization_payload, field: value}
        first = client.post("/organizations/", json=first_payload)
        assert first.status_code == 200, first.text
        duplicate = {**organization_payload, "org_code": "SECOND", field: value}
        assert client.post("/organizations/", json=duplicate).status_code == 409
        second = client.post("/organizations/", json={
            **organization_payload, "org_code": "SECOND"
        }).json()
        assert client.put(f"/organizations/{second['id']}", json={field: value}).status_code == 409
        assert client.put(f"/organizations/{first.json()['id']}", json={field: value}).status_code == 200

    def test_delete_with_companies_is_restricted(self, client, db_session, organization):
        company = Company(
            organization_id=organization.id, company_name="Tenant Company",
            industry="Technology", company_type="Private"
        )
        db_session.add(company)
        db_session.commit()
        response = client.delete(f"/organizations/{organization.id}")
        assert response.status_code == 409
        assert db_session.get(Company, company.id).organization_id == organization.id
        assert client.get(f"/organizations/{organization.id}").status_code == 200

    @pytest.mark.parametrize("method", ["get", "put", "delete"])
    def test_missing(self, client, method):
        kwargs = {"json": {}} if method == "put" else {}
        assert getattr(client, method)("/organizations/99999", **kwargs).status_code == 404

    def test_validation_and_pagination(self, client, organization_payload):
        assert client.post("/organizations/", json={
            **organization_payload, "email": "invalid"
        }).status_code == 422
        created = client.post("/organizations/", json=organization_payload).json()
        assert client.put(f"/organizations/{created['id']}", json={"status": None}).status_code == 422
        assert client.put(f"/organizations/{created['id']}", json={"public_id": "new"}).status_code == 422
        assert client.get("/organizations/?skip=-1").status_code == 422
        assert client.get("/organizations/?limit=0").status_code == 422
        assert client.get("/organizations/?skip=1&limit=1").json() == []

    @pytest.mark.parametrize("method,path", [
        ("get", "/organizations/"), ("get", "/organizations/1"),
        ("get", "/organizations/code/ORG-API"),
        ("get", "/organizations/public-id/00000000-0000-0000-0000-000000000000"),
        ("post", "/organizations/"), ("put", "/organizations/1"),
        ("delete", "/organizations/1"),
    ])
    def test_authentication_required(self, client, organization_payload, method, path):
        client.app.dependency_overrides.pop(get_current_user)
        assert client.request(method, path, json=organization_payload).status_code == 401

    @pytest.mark.parametrize("method,path", [
        ("post", "/organizations/"), ("put", "/organizations/1"),
        ("delete", "/organizations/1"),
    ])
    def test_non_admin_cannot_write(self, client, organization_payload, method, path):
        client.app.dependency_overrides[get_current_user] = lambda: User(
            id=2, email="user@example.com", role="user"
        )
        assert client.request(method, path, json=organization_payload).status_code == 403
        assert client.get("/organizations/").status_code == 200


class TestOrganizationMigration:
    def test_postgresql_enum_lifecycle(self):
        import importlib.util
        from pathlib import Path

        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        from sqlalchemy import create_mock_engine

        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / (
            "f1e2d3c4b5a6_create_industries_and_organizations_tables.py"
        )
        spec = importlib.util.spec_from_file_location("organization_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        statements = []
        engine = create_mock_engine(
            "postgresql://", lambda sql, *args, **kwargs: statements.append(
                str(sql.compile(dialect=engine.dialect))
            )
        )
        migration.op = Operations(MigrationContext.configure(engine))
        migration.upgrade()
        for name in ("orgtype", "subscriptiontier", "organizationstatus"):
            assert sum(f"CREATE TYPE {name} AS ENUM" in sql for sql in statements) == 1
        assert any("settings JSONB" in sql for sql in statements)
        statements.clear()
        migration.downgrade()
        table_drop = next(i for i, sql in enumerate(statements) if "DROP TABLE organizations" in sql)
        for name in ("orgtype", "subscriptiontier", "organizationstatus"):
            type_drop = next(i for i, sql in enumerate(statements) if f"DROP TYPE {name}" in sql)
            assert table_drop < type_drop