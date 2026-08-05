"""Unit tests for the Decision Maker domain."""

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
    PreferredContact,
)
from app.repositories.decision_maker import DecisionMakerRepository

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
def decision_maker_payload(company):
    return {
        "company_id": company.id,
        "full_name": "John Doe",
        "designation": "CTO",
        "decision_level": "C_SUITE",
        "preferred_contact": "EMAIL",
        "decision_maker_status": "NEW",
        "email": "john.doe@acme.com",
        "phone": "+91-9876543210",
        "linkedin_url": "https://www.linkedin.com/in/johndoe",
        "is_primary_contact": True,
        "notes": "Key technical decision maker.",
    }


class TestDecisionMakerModel:
    def test_create_decision_maker(self, db_session, company):
        decision_maker = DecisionMaker(
            company_id=company.id,
            full_name="Jane Smith",
            designation="VP Procurement",
            decision_level=DecisionLevel.VP,
            preferred_contact=PreferredContact.LINKEDIN,
            decision_maker_status=DecisionMakerStatus.CONTACTED,
            email="jane.smith@acme.com",
        )
        db_session.add(decision_maker)
        db_session.commit()
        db_session.refresh(decision_maker)

        assert decision_maker.id is not None
        assert decision_maker.full_name == "Jane Smith"
        assert decision_maker.company_id == company.id
        assert decision_maker.decision_level == DecisionLevel.VP
        assert decision_maker.decision_maker_status == DecisionMakerStatus.CONTACTED
        assert decision_maker.is_primary_contact is False

    def test_company_relationship(self, db_session, company):
        decision_maker = DecisionMaker(
            company_id=company.id,
            full_name="Jane Smith",
            designation="VP Procurement",
            decision_level=DecisionLevel.VP,
            decision_maker_status=DecisionMakerStatus.NEW,
        )
        db_session.add(decision_maker)
        db_session.commit()

        assert decision_maker in company.decision_makers
        assert decision_maker.company is company


class TestDecisionMakerRepository:
    def test_create(self, db_session, decision_maker_payload):
        repository = DecisionMakerRepository()
        decision_maker = repository.create(
            db_session,
            DecisionMaker(**decision_maker_payload),
        )

        assert decision_maker.id is not None
        assert decision_maker.full_name == "John Doe"

    def test_get_by_id(self, db_session, decision_maker_payload):
        repository = DecisionMakerRepository()
        created = repository.create(
            db_session,
            DecisionMaker(**decision_maker_payload),
        )

        fetched = repository.get_by_id(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    def test_list_by_company(self, db_session, company, decision_maker_payload):
        repository = DecisionMakerRepository()
        repository.create(
            db_session,
            DecisionMaker(**decision_maker_payload),
        )
        repository.create(
            db_session,
            DecisionMaker(
                company_id=company.id,
                full_name="Jane Smith",
                designation="VP",
                decision_level=DecisionLevel.VP,
                preferred_contact=PreferredContact.EMAIL,
                decision_maker_status=DecisionMakerStatus.NEW,
                email="jane.smith@acme.com",
            ),
        )

        results = repository.get_by_company_id(db_session, company.id)

        assert len(results) == 2

    def test_update(self, db_session, decision_maker_payload):
        repository = DecisionMakerRepository()
        created = repository.create(
            db_session,
            DecisionMaker(**decision_maker_payload),
        )

        created.full_name = "John Doe Jr."
        created.decision_maker_status = DecisionMakerStatus.CONTACTED
        updated = repository.update(db_session, created)

        assert updated.full_name == "John Doe Jr."
        assert updated.decision_maker_status == DecisionMakerStatus.CONTACTED

    def test_delete(self, db_session, decision_maker_payload):
        repository = DecisionMakerRepository()
        created = repository.create(
            db_session,
            DecisionMaker(**decision_maker_payload),
        )

        repository.delete(db_session, created)

        assert repository.get_by_id(db_session, created.id) is None