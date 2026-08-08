"""Unit tests for the WarehouseMatch domain."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
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
    Requirement,
    RequirementStatus,
    User,
    Warehouse,
    AvailabilityStatus,
    MatchedBy,
    WarehouseMatch,
    WarehouseMatchStatus,
    WarehouseType,
)
from app.repositories.warehouse_match import WarehouseMatchRepository
from app.schemas.warehouse_match import (
    WarehouseMatchCreate,
    WarehouseMatchUpdate,
)
from app.services.warehouse_match import WarehouseMatchService

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
def reviewer(db_session):
    reviewer = User(
        full_name="Reviewer",
        email="reviewer@bhoodevi.com",
        hashed_password="hashed",
    )
    db_session.add(reviewer)
    db_session.commit()
    db_session.refresh(reviewer)
    return reviewer


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
def warehouse(db_session, user):
    warehouse = Warehouse(
        warehouse_name="Greenfield Logistics Park",
        warehouse_code="WH-001",
        warehouse_type=WarehouseType.COVERED,
        total_area_sqft=100000,
        city="Pune",
        state="Maharashtra",
        owner_id=user.id,
        availability_status=AvailabilityStatus.AVAILABLE,
    )
    db_session.add(warehouse)
    db_session.commit()
    db_session.refresh(warehouse)
    return warehouse


@pytest.fixture()
def warehouse_2(db_session, user):
    warehouse = Warehouse(
        warehouse_name="Second Logistics Park",
        warehouse_code="WH-002",
        warehouse_type=WarehouseType.COVERED,
        total_area_sqft=50000,
        city="Pune",
        state="Maharashtra",
        owner_id=user.id,
        availability_status=AvailabilityStatus.AVAILABLE,
    )
    db_session.add(warehouse)
    db_session.commit()
    db_session.refresh(warehouse)
    return warehouse


@pytest.fixture()
def requirement(db_session, lead):
    requirement = Requirement(
        lead_id=lead.id,
        title="Need 50,000 sqft warehouse in Pune",
        requirement_status=RequirementStatus.ACTIVE,
    )
    db_session.add(requirement)
    db_session.commit()
    db_session.refresh(requirement)
    return requirement


@pytest.fixture()
def match_payload(lead, warehouse):
    return {
        "lead_id": lead.id,
        "warehouse_id": warehouse.id,
        "status": "SHORTLISTED",
        "matched_by": "MANUAL",
        "requirement_id": None,
        "match_score": 85.5,
        "match_rank": 1,
        "geo_distance_km": 12.5,
        "transit_days": 2,
        "capacity_fit": 90,
        "budget_fit": 80,
        "requirement_compatibility": "Exceeds all hard requirements",
        "match_reasons": "Location within radius; capacity matches",
        "concern_reasons": "Rent slightly above budget",
        "top_reason": "Best location fit",
        "model_id": "manual-review",
        "model_version": "1.0",
        "reviewed_by_user_id": None,
        "reviewed_at": None,
        "notes": "Shortlisted after site visit",
    }


class TestWarehouseMatchModel:
    def test_create_warehouse_match(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()
        db_session.refresh(match)

        assert match.id is not None
        assert match.lead_id == lead.id
        assert match.warehouse_id == warehouse.id
        assert match.status == WarehouseMatchStatus.SHORTLISTED
        assert match.matched_by == MatchedBy.MANUAL
        assert match.match_score == 85.5
        assert match.created_at is not None

    def test_status_and_matched_by_are_required(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            match_score=50,
        )
        db_session.add(match)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_match_score_range_constraint(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=150,
        )
        db_session.add(match)
        with pytest.raises(Exception):
            db_session.commit()
        db_session.rollback()

    def test_warehouse_relationship(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        assert match.warehouse is warehouse

    def test_lead_relationship(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        assert match.lead is lead

    def test_lead_warehouse_matches_collection(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        assert lead.warehouse_matches[0] is match

    def test_warehouse_matches_collection(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        assert warehouse.matches[0] is match

    def test_deleting_lead_cascades_matches(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        db_session.delete(lead)
        db_session.commit()

        assert db_session.get(WarehouseMatch, match.id) is None

    def test_partial_unique_indexes_defined(self):
        table = WarehouseMatch.__table__
        index_names = {i.name for i in table.indexes}

        # Approved design uses partial unique indexes only (no plain unique
        # constraints on (requirement_id, warehouse_id) / (lead_id, warehouse_id)).
        assert "uq_warehouse_matches__lead__warehouse__partial" in index_names
        assert "uq_warehouse_matches__requirement__warehouse__partial" in index_names

        lead_warehouse_idx = next(
            i for i in table.indexes if i.name == "uq_warehouse_matches__lead__warehouse__partial"
        )
        requirement_warehouse_idx = next(
            i for i in table.indexes if i.name == "uq_warehouse_matches__requirement__warehouse__partial"
        )

        assert lead_warehouse_idx.unique is True
        assert requirement_warehouse_idx.unique is True
        assert lead_warehouse_idx.dialect_options["sqlite"]["where"].text == (
            "requirement_id IS NULL"
        )
        assert requirement_warehouse_idx.dialect_options["sqlite"]["where"].text == (
            "requirement_id IS NOT NULL"
        )

    def test_duplicate_lead_warehouse_rejected(self, db_session, lead, warehouse):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        duplicate = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=70,
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_duplicate_requirement_warehouse_rejected(
        self,
        db_session,
        lead,
        warehouse,
        requirement,
    ):
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            requirement_id=requirement.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        duplicate = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            requirement_id=requirement.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=70,
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_same_warehouse_different_requirements_allowed(
        self,
        db_session,
        lead,
        warehouse,
        requirement,
    ):
        # First match is scoped to requirement 1 (requirement_id non-null).
        match = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            requirement_id=requirement.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=85.5,
        )
        db_session.add(match)
        db_session.commit()

        requirement_2 = Requirement(
            lead_id=lead.id,
            title="Need 30,000 sqft warehouse in Mumbai",
            requirement_status=RequirementStatus.ACTIVE,
        )
        db_session.add(requirement_2)
        db_session.commit()

        # A different requirement for the same warehouse is allowed: the partial
        # unique index on (requirement_id, warehouse_id) only enforces one match
        # per requirement+warehouse pair.
        match_2 = WarehouseMatch(
            lead_id=lead.id,
            warehouse_id=warehouse.id,
            requirement_id=requirement_2.id,
            status=WarehouseMatchStatus.SHORTLISTED,
            matched_by=MatchedBy.MANUAL,
            match_score=80,
        )
        db_session.add(match_2)
        db_session.commit()

        assert match_2.id is not None
        assert db_session.query(WarehouseMatch).filter(
            WarehouseMatch.warehouse_id == warehouse.id
        ).count() == 2


class TestWarehouseMatchRepository:
    def test_create(self, db_session, match_payload):
        repository = WarehouseMatchRepository()
        match = repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        assert match.id is not None
        assert match.status == WarehouseMatchStatus.SHORTLISTED
        assert match.match_score == 85.5

    def test_get_by_id(self, db_session, match_payload):
        repository = WarehouseMatchRepository()
        created = repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        fetched = repository.get_by_id(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    def test_get_matches_for_lead(self, db_session, lead, warehouse, warehouse_2, match_payload):
        repository = WarehouseMatchRepository()
        repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )
        match_payload["match_score"] = 70
        match_payload["warehouse_id"] = warehouse_2.id
        repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        results = repository.get_matches_for_lead(db_session, lead.id)

        assert len(results) == 2
        assert results[0].match_score == 85.5

    def test_get_matches_for_warehouse(self, db_session, warehouse, match_payload):
        repository = WarehouseMatchRepository()
        repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        results = repository.get_matches_for_warehouse(
            db_session,
            warehouse.id,
        )

        assert len(results) == 1
        assert results[0].warehouse_id == warehouse.id

    def test_get_matches_for_requirement(self, db_session, requirement, match_payload):
        repository = WarehouseMatchRepository()
        match_payload["requirement_id"] = requirement.id
        repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        results = repository.get_matches_for_requirement(
            db_session,
            requirement.id,
        )

        assert len(results) == 1
        assert results[0].requirement_id == requirement.id

    def test_get_by_lead_and_warehouse(self, db_session, lead, warehouse, match_payload):
        repository = WarehouseMatchRepository()
        repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        found = repository.get_by_lead_and_warehouse(
            db_session,
            lead.id,
            warehouse.id,
        )

        assert found is not None
        assert found.lead_id == lead.id
        assert found.warehouse_id == warehouse.id

    def test_update(self, db_session, match_payload):
        repository = WarehouseMatchRepository()
        created = repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        created.status = WarehouseMatchStatus.LEAD_CHOSEN
        updated = repository.update(db_session, created)

        assert updated.status == WarehouseMatchStatus.LEAD_CHOSEN

    def test_delete(self, db_session, match_payload):
        repository = WarehouseMatchRepository()
        created = repository.create(
            db_session,
            WarehouseMatch(**match_payload),
        )

        repository.delete(db_session, created)

        assert repository.get_by_id(db_session, created.id) is None


class TestWarehouseMatchService:
    def test_create_match(self, db_session, match_payload):
        service = WarehouseMatchService()
        match = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        assert match is not None
        assert match.id is not None
        assert match.status == WarehouseMatchStatus.SHORTLISTED
        assert match.match_score == 85.5

    def test_create_match_lead_not_found(self, db_session, match_payload):
        service = WarehouseMatchService()
        match_payload["lead_id"] = 9999
        match = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        assert match is None

    def test_create_match_warehouse_not_found(self, db_session, match_payload):
        service = WarehouseMatchService()
        match_payload["warehouse_id"] = 9999
        match = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        assert match is None

    def test_create_match_requirement_not_found(self, db_session, match_payload):
        service = WarehouseMatchService()
        match_payload["requirement_id"] = 9999
        match = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        assert match is None

    def test_create_match_with_requirement(self, db_session, requirement, match_payload):
        service = WarehouseMatchService()
        match_payload["requirement_id"] = requirement.id
        match = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        assert match is not None
        assert match.requirement_id == requirement.id

    def test_get_match_by_id(self, db_session, match_payload):
        service = WarehouseMatchService()
        created = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        fetched = service.get_match_by_id(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    def test_list_matches_for_lead(self, db_session, match_payload, warehouse_2):
        service = WarehouseMatchService()
        service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )
        match_payload["match_score"] = 70
        match_payload["warehouse_id"] = warehouse_2.id
        service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        results = service.list_matches_for_lead(
            db_session,
            match_payload["lead_id"],
        )

        assert len(results) == 2

    def test_list_matches_for_warehouse(self, db_session, match_payload):
        service = WarehouseMatchService()
        service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        results = service.list_matches_for_warehouse(
            db_session,
            match_payload["warehouse_id"],
        )

        assert len(results) == 1

    def test_list_matches_for_requirement(self, db_session, requirement, match_payload):
        service = WarehouseMatchService()
        match_payload["requirement_id"] = requirement.id
        service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        results = service.list_matches_for_requirement(
            db_session,
            requirement.id,
        )

        assert len(results) == 1

    def test_update_match(self, db_session, match_payload):
        service = WarehouseMatchService()
        created = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        updated = service.update_match(
            db_session,
            created.id,
            WarehouseMatchUpdate(
                status="LEAD_CHOSEN",
                notes="Client shortlisted for proposal",
            ),
        )

        assert updated is not None
        assert updated.status == WarehouseMatchStatus.LEAD_CHOSEN
        assert updated.notes == "Client shortlisted for proposal"

    def test_update_match_not_found(self, db_session):
        service = WarehouseMatchService()
        updated = service.update_match(
            db_session,
            9999,
            WarehouseMatchUpdate(status="REJECTED"),
        )

        assert updated is None

    def test_update_match_invalid_lead(self, db_session, match_payload):
        service = WarehouseMatchService()
        created = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        updated = service.update_match(
            db_session,
            created.id,
            WarehouseMatchUpdate(lead_id=9999),
        )

        assert updated is None

    def test_update_match_invalid_warehouse(self, db_session, match_payload):
        service = WarehouseMatchService()
        created = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        updated = service.update_match(
            db_session,
            created.id,
            WarehouseMatchUpdate(warehouse_id=9999),
        )

        assert updated is None

    def test_update_match_invalid_requirement(self, db_session, match_payload):
        service = WarehouseMatchService()
        created = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        updated = service.update_match(
            db_session,
            created.id,
            WarehouseMatchUpdate(requirement_id=9999),
        )

        assert updated is None

    def test_update_match_clear_requirement(self, db_session, requirement, match_payload):
        service = WarehouseMatchService()
        match_payload["requirement_id"] = requirement.id
        created = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        updated = service.update_match(
            db_session,
            created.id,
            WarehouseMatchUpdate(requirement_id=None),
        )

        assert updated is not None
        assert updated.requirement_id is None

    def test_delete_match(self, db_session, match_payload):
        service = WarehouseMatchService()
        created = service.create_match(
            db_session,
            WarehouseMatchCreate(**match_payload),
        )

        deleted = service.delete_match(db_session, created.id)

        assert deleted is not None
        assert service.get_match_by_id(db_session, created.id) is None

    def test_delete_match_not_found(self, db_session):
        service = WarehouseMatchService()
        deleted = service.delete_match(db_session, 9999)

        assert deleted is None