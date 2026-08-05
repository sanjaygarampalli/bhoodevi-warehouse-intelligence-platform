"""Unit tests for the Lead domain."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.dependencies import get_db
from app.main import app
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
    User,
)
from app.repositories.lead import LeadRepository

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
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def lead_payload(company, decision_maker, user):
    return {
        "lead_number": "LEAD-0001",
        "company_id": company.id,
        "status": "NEW",
        "lead_source": "MANUAL",
        "space_needed_sqft": 5000,
        "requirement_type": "WAREHOUSE",
        "target_industry": "FMCG",
        "preferred_city": "Mumbai",
        "preferred_state": "Maharashtra",
        "preferred_country": "India",
        "expected_monthly_rent": 250000,
        "currency": "INR",
        "move_in_timeframe": "3_6_MONTHS",
        "lease_tenure_years": 5,
        "owner_user_id": user.id,
        "primary_decision_maker_id": decision_maker.id,
        "priority": "HIGH",
    }


class TestLeadModel:
    def test_create_lead(self, db_session, company, decision_maker, user):
        lead = Lead(
            lead_number="LEAD-1001",
            company_id=company.id,
            status=LeadStatus.NEW,
            lead_source=LeadSource.MANUAL,
            space_needed_sqft=Decimal("5000"),
            requirement_type="WAREHOUSE",
            target_industry="FMCG",
            preferred_city="Mumbai",
            preferred_state="Maharashtra",
            preferred_country="India",
            expected_monthly_rent=Decimal("250000"),
            currency="INR",
            move_in_timeframe=MoveInTimeframe.THREE_TO_SIX_MONTHS,
            lease_tenure_years=5,
            owner_user_id=user.id,
            primary_decision_maker_id=decision_maker.id,
            ai_score=Decimal("85"),
            priority=LeadPriority.HIGH,
        )
        db_session.add(lead)
        db_session.commit()
        db_session.refresh(lead)

        assert lead.id is not None
        assert lead.lead_number == "LEAD-1001"
        assert lead.company_id == company.id
        assert lead.status == LeadStatus.NEW
        assert lead.lead_source == LeadSource.MANUAL
        assert lead.move_in_timeframe == MoveInTimeframe.THREE_TO_SIX_MONTHS
        assert lead.priority == LeadPriority.HIGH
        assert lead.primary_decision_maker_id == decision_maker.id
        assert lead.owner_user_id == user.id

    def test_company_relationship(self, db_session, company):
        lead = Lead(
            lead_number="LEAD-1002",
            company_id=company.id,
        )
        db_session.add(lead)
        db_session.commit()

        assert lead.company is company

    def test_primary_decision_maker_relationship(self, db_session, company, decision_maker):
        lead = Lead(
            lead_number="LEAD-1003",
            company_id=company.id,
            primary_decision_maker_id=decision_maker.id,
        )
        db_session.add(lead)
        db_session.commit()

        assert lead.primary_decision_maker is decision_maker

    def test_owner_user_relationship(self, db_session, company, user):
        lead = Lead(
            lead_number="LEAD-1004",
            company_id=company.id,
            owner_user_id=user.id,
        )
        db_session.add(lead)
        db_session.commit()

        assert lead.owner_user is user


class TestLeadRepository:
    def test_create(self, db_session, lead_payload):
        repository = LeadRepository()
        lead = repository.create(
            db_session,
            Lead(**lead_payload),
        )

        assert lead.id is not None
        assert lead.lead_number == "LEAD-0001"

    def test_get_by_id(self, db_session, lead_payload):
        repository = LeadRepository()
        created = repository.create(
            db_session,
            Lead(**lead_payload),
        )

        fetched = repository.get_by_id(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    def test_list_by_company(self, db_session, company):
        repository = LeadRepository()
        repository.create(
            db_session,
            Lead(
                lead_number="LEAD-0001",
                company_id=company.id,
            ),
        )
        repository.create(
            db_session,
            Lead(
                lead_number="LEAD-0002",
                company_id=company.id,
                status=LeadStatus.DISCOVERED,
                lead_source=LeadSource.LINKEDIN,
                priority=LeadPriority.URGENT,
            ),
        )

        results = repository.get_by_company_id(db_session, company.id)

        assert len(results) == 2

    def test_update(self, db_session, lead_payload):
        repository = LeadRepository()
        created = repository.create(
            db_session,
            Lead(**lead_payload),
        )

        created.status = LeadStatus.CONTACTED
        created.space_needed_sqft = Decimal("8000")
        updated = repository.update(db_session, created)

        assert updated.status == LeadStatus.CONTACTED
        assert updated.space_needed_sqft == Decimal("8000")

    def test_delete(self, db_session, lead_payload):
        repository = LeadRepository()
        created = repository.create(
            db_session,
            Lead(**lead_payload),
        )

        repository.delete(db_session, created)

        assert repository.get_by_id(db_session, created.id) is None