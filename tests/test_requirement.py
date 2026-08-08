"""Unit tests for the Requirement domain."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import (
    Company,
    DecisionLevel,
    DecisionMaker,
    DecisionMakerStatus,
    Lead,
    LeadPriority,
    LeadSource,
    LeadStatus,
    MoveInTimeframe,
    Requirement,
    RequirementStatus,
    User,
    WarehouseType,
)
from app.repositories.requirement import RequirementRepository
from app.schemas.requirement import (
    RequirementCreate,
    RequirementUpdate,
)
from app.services.requirement import RequirementService

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def company(db_session):
    company = Company(
        company_name="Acme Corp",
        industry="Manufacturing",
        company_type="Private",
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture()
def decision_maker(db_session, company):
    decision_maker = DecisionMaker(
        company_id=company.id,
        full_name="John Doe",
        designation="CTO",
        decision_level=DecisionLevel.C_SUITE,
        decision_maker_status=DecisionMakerStatus.NEW,
        email="john.doe@acme.com",
        is_primary_contact=True,
    )
    db_session.add(decision_maker)
    db_session.commit()
    db_session.refresh(decision_maker)
    return decision_maker


@pytest.fixture()
def user(db_session):
    user = User(
        full_name="Sales Rep",
        email="sales@bhoodevi.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def lead(db_session, company, decision_maker, user):
    lead = Lead(
        lead_number="LEAD-0001",
        company_id=company.id,
        status=LeadStatus.NEW,
        lead_source=LeadSource.MANUAL,
        owner_user_id=user.id,
        primary_decision_maker_id=decision_maker.id,
        priority=LeadPriority.HIGH,
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


@pytest.fixture()
def requirement_payload(lead):
    return {
        "lead_id": lead.id,
        "title": "Need 50,000 sqft warehouse in Pune",
        "description": "Client needs a Grade-A warehouse with cold storage",
        "required_builtup_area": 50000,
        "required_open_area": 10000,
        "minimum_area": 40000,
        "maximum_area": 60000,
        "industry": "FMCG",
        "goods_type": "Frozen Food",
        "storage_type": "Cold Storage",
        "compliance_requirements": "FSSAI compliant",
        "preferred_state": "Maharashtra",
        "preferred_city": "Pune",
        "preferred_locality": "Chakan",
        "preferred_pincode": "410501",
        "radius_km": 50,
        "latitude": 18.6515,
        "longitude": 73.7598,
        "budget_per_sqft": 25,
        "lease_duration_months": 36,
        "security_deposit_months": 6,
        "preferred_lease_type": "LEASE",
        "escalation_percentage": 5,
        "warehouse_type": "COLD_STORAGE",
        "required_clear_height": 9.5,
        "required_floor_load": 2.5,
        "required_power_load": 500,
        "required_docks": 4,
        "truck_parking_required": True,
        "rail_connectivity_required": False,
        "fire_noc_required": True,
        "temperature_controlled": True,
        "loading_bays_required": 2,
        "dock_level_required": True,
        "ground_level_required": False,
        "office_required": True,
        "labour_required": True,
        "operating_hours": "24/7",
        "expected_monthly_dispatch": 100000,
        "expected_monthly_receipts": 120000,
        "move_in_timeframe": "3_6_MONTHS",
    }


class TestRequirementModel:
    def test_create_requirement(self, db_session, lead):
        requirement = Requirement(
            lead_id=lead.id,
            title="Need 50,000 sqft warehouse in Pune",
            description="Client needs a Grade-A warehouse",
            required_builtup_area=50000,
            industry="FMCG",
            warehouse_type=WarehouseType.COLD_STORAGE,
            requirement_status=RequirementStatus.ACTIVE,
        )
        db_session.add(requirement)
        db_session.commit()
        db_session.refresh(requirement)

        assert requirement.id is not None
        assert requirement.lead_id == lead.id
        assert requirement.title == "Need 50,000 sqft warehouse in Pune"
        assert requirement.required_builtup_area == 50000
        assert requirement.warehouse_type == WarehouseType.COLD_STORAGE
        assert requirement.requirement_status == RequirementStatus.ACTIVE
        assert requirement.created_at is not None

    def test_default_status_is_draft(self, db_session, lead):
        requirement = Requirement(
            lead_id=lead.id,
            title="Default status check",
        )
        db_session.add(requirement)
        db_session.commit()
        db_session.refresh(requirement)

        assert requirement.requirement_status == RequirementStatus.DRAFT

    def test_lead_relationship(self, db_session, lead):
        requirement = Requirement(
            lead_id=lead.id,
            title="Relationship check",
        )
        db_session.add(requirement)
        db_session.commit()

        assert requirement.lead is lead

    def test_lead_requirements_collection(self, db_session, lead):
        requirement = Requirement(
            lead_id=lead.id,
            title="Collection check",
        )
        db_session.add(requirement)
        db_session.commit()

        assert lead.requirements[0] is requirement

    def test_deleting_lead_cascades_requirements(self, db_session, lead):
        requirement = Requirement(
            lead_id=lead.id,
            title="Cascade check",
        )
        db_session.add(requirement)
        db_session.commit()

        db_session.delete(lead)
        db_session.commit()

        assert db_session.get(Requirement, requirement.id) is None


class TestRequirementRepository:
    def test_create(self, db_session, requirement_payload):
        repository = RequirementRepository()
        requirement = repository.create(
            db_session,
            Requirement(**requirement_payload),
        )

        assert requirement.id is not None
        assert requirement.title == "Need 50,000 sqft warehouse in Pune"

    def test_get_by_id(self, db_session, requirement_payload):
        repository = RequirementRepository()
        created = repository.create(
            db_session,
            Requirement(**requirement_payload),
        )

        fetched = repository.get_by_id(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    def test_list_by_lead(self, db_session, lead):
        repository = RequirementRepository()
        repository.create(
            db_session,
            Requirement(
                lead_id=lead.id,
                title="First requirement",
            ),
        )
        repository.create(
            db_session,
            Requirement(
                lead_id=lead.id,
                title="Second requirement",
            ),
        )

        results = repository.get_by_lead_id(db_session, lead.id)

        assert len(results) == 2

    def test_update(self, db_session, requirement_payload):
        repository = RequirementRepository()
        created = repository.create(
            db_session,
            Requirement(**requirement_payload),
        )

        created.requirement_status = RequirementStatus.CLOSED
        updated = repository.update(db_session, created)

        assert updated.requirement_status == RequirementStatus.CLOSED

    def test_delete(self, db_session, requirement_payload):
        repository = RequirementRepository()
        created = repository.create(
            db_session,
            Requirement(**requirement_payload),
        )

        repository.delete(db_session, created)

        assert repository.get_by_id(db_session, created.id) is None


class TestRequirementService:
    def test_create_requirement(self, db_session, requirement_payload):
        service = RequirementService()
        requirement = service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )

        assert requirement is not None
        assert requirement.id is not None
        assert requirement.title == "Need 50,000 sqft warehouse in Pune"

    def test_create_requirement_lead_not_found(self, db_session, requirement_payload):
        service = RequirementService()
        requirement_payload["lead_id"] = 9999
        requirement = service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )

        assert requirement is None

    def test_get_requirement_by_id(self, db_session, requirement_payload):
        service = RequirementService()
        created = service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )

        fetched = service.get_requirement_by_id(
            db_session,
            created.id,
        )

        assert fetched is not None
        assert fetched.id == created.id

    def test_list_requirements_by_lead(self, db_session, requirement_payload):
        service = RequirementService()
        service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )
        requirement_payload["title"] = "Second requirement"
        service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )

        results = service.list_requirements_by_lead(
            db_session,
            requirement_payload["lead_id"],
        )

        assert len(results) == 2

    def test_update_requirement(self, db_session, requirement_payload):
        service = RequirementService()
        created = service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )

        updated = service.update_requirement(
            db_session,
            created.id,
            RequirementUpdate(
                title="Updated warehouse requirement",
                requirement_status="CLOSED",
            ),
        )

        assert updated is not None
        assert updated.title == "Updated warehouse requirement"
        assert updated.requirement_status == RequirementStatus.CLOSED

    def test_update_requirement_not_found(self, db_session):
        service = RequirementService()
        updated = service.update_requirement(
            db_session,
            9999,
            RequirementUpdate(title="Nope"),
        )

        assert updated is None

    def test_update_requirement_invalid_lead(self, db_session, requirement_payload):
        service = RequirementService()
        created = service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )

        updated = service.update_requirement(
            db_session,
            created.id,
            RequirementUpdate(lead_id=9999),
        )

        assert updated is None

    def test_delete_requirement(self, db_session, requirement_payload):
        service = RequirementService()
        created = service.create_requirement(
            db_session,
            RequirementCreate(**requirement_payload),
        )

        deleted = service.delete_requirement(
            db_session,
            created.id,
        )

        assert deleted is not None
        assert service.get_requirement_by_id(db_session, created.id) is None

    def test_delete_requirement_not_found(self, db_session):
        service = RequirementService()
        deleted = service.delete_requirement(db_session, 9999)

        assert deleted is None