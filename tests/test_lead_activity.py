"""Unit tests for the Lead Activity domain."""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models import (
    ActivityChannel,
    ActivityOutcome,
    ActivitySourceType,
    ActivityStatus,
    ActivityType,
    Company,
    DecisionLevel,
    DecisionMaker,
    DecisionMakerStatus,
    Lead,
    LeadActivity,
    LeadPriority,
    LeadSource,
    LeadStatus,
    MoveInTimeframe,
    User,
)
from app.repositories.lead_activity import LeadActivityRepository
from app.schemas.lead_activity import (
    LeadActivityCreate,
    LeadActivityUpdate,
)
from app.services.lead_activity import LeadActivityService

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
def activity_payload(lead, user):
    return {
        "lead_id": lead.id,
        "activity_type": "CALL",
        "subject": "Introductory call",
        "description": "Discussed warehouse requirements",
        "next_followup_date": datetime(2026, 8, 10, 10, 0, 0),
        "status": "SCHEDULED",
        "performed_by": user.id,
        "channel": "PHONE",
        "duration_minutes": 30,
    }


class TestLeadActivityModel:
    def test_create_lead_activity(self, db_session, lead, user):
        activity = LeadActivity(
            lead_id=lead.id,
            activity_type=ActivityType.CALL,
            subject="Introductory call",
            description="Discussed warehouse requirements",
            status=ActivityStatus.SCHEDULED,
            performed_by=user.id,
            channel=ActivityChannel.PHONE,
            duration_minutes=30,
        )
        db_session.add(activity)
        db_session.commit()
        db_session.refresh(activity)

        assert activity.id is not None
        assert activity.lead_id == lead.id
        assert activity.activity_type == ActivityType.CALL
        assert activity.subject == "Introductory call"
        assert activity.status == ActivityStatus.SCHEDULED
        assert activity.channel == ActivityChannel.PHONE
        assert activity.performed_by == user.id
        assert activity.activity_date is not None

    def test_lead_relationship(self, db_session, lead):
        activity = LeadActivity(
            lead_id=lead.id,
            activity_type=ActivityType.EMAIL,
            subject="Follow up email",
        )
        db_session.add(activity)
        db_session.commit()

        assert activity.lead is lead

    def test_lead_activities_collection(self, db_session, lead):
        activity = LeadActivity(
            lead_id=lead.id,
            activity_type=ActivityType.NOTE,
            subject="Internal note",
        )
        db_session.add(activity)
        db_session.commit()

        assert lead.activities[0] is activity


class TestLeadActivityRepository:
    def test_create(self, db_session, activity_payload):
        repository = LeadActivityRepository()
        activity = repository.create(
            db_session,
            LeadActivity(**activity_payload),
        )

        assert activity.id is not None
        assert activity.subject == "Introductory call"

    def test_get_by_id(self, db_session, activity_payload):
        repository = LeadActivityRepository()
        created = repository.create(
            db_session,
            LeadActivity(**activity_payload),
        )

        fetched = repository.get_by_id(db_session, created.id)

        assert fetched is not None
        assert fetched.id == created.id

    def test_list_by_lead(self, db_session, lead):
        repository = LeadActivityRepository()
        repository.create(
            db_session,
            LeadActivity(
                lead_id=lead.id,
                activity_type=ActivityType.CALL,
                subject="First call",
            ),
        )
        repository.create(
            db_session,
            LeadActivity(
                lead_id=lead.id,
                activity_type=ActivityType.EMAIL,
                subject="Follow up email",
                status=ActivityStatus.COMPLETED,
            ),
        )

        results = repository.get_by_lead_id(db_session, lead.id)

        assert len(results) == 2

    def test_update(self, db_session, activity_payload):
        repository = LeadActivityRepository()
        created = repository.create(
            db_session,
            LeadActivity(**activity_payload),
        )

        created.status = ActivityStatus.COMPLETED
        created.outcome = ActivityOutcome.INTERESTED
        updated = repository.update(db_session, created)

        assert updated.status == ActivityStatus.COMPLETED
        assert updated.outcome == ActivityOutcome.INTERESTED

    def test_delete(self, db_session, activity_payload):
        repository = LeadActivityRepository()
        created = repository.create(
            db_session,
            LeadActivity(**activity_payload),
        )

        repository.delete(db_session, created)

        assert repository.get_by_id(db_session, created.id) is None


class TestLeadActivityService:
    def test_create_activity(self, db_session, activity_payload):
        service = LeadActivityService()
        activity = service.create_lead_activity(
            db_session,
            LeadActivityCreate(**activity_payload),
        )

        assert activity is not None
        assert activity.id is not None
        assert activity.subject == "Introductory call"

    def test_create_activity_lead_not_found(self, db_session, activity_payload):
        service = LeadActivityService()
        activity_payload["lead_id"] = 9999
        activity = service.create_lead_activity(
            db_session,
            LeadActivityCreate(**activity_payload),
        )

        assert activity is None

    def test_get_activity_by_id(self, db_session, activity_payload):
        service = LeadActivityService()
        created = service.create_lead_activity(
            db_session,
            LeadActivityCreate(**activity_payload),
        )

        fetched = service.get_lead_activity_by_id(
            db_session,
            created.id,
        )

        assert fetched is not None
        assert fetched.id == created.id

    def test_list_activities_by_lead(self, db_session, activity_payload):
        service = LeadActivityService()
        service.create_lead_activity(
            db_session,
            LeadActivityCreate(**activity_payload),
        )
        activity_payload["activity_type"] = "EMAIL"
        activity_payload["subject"] = "Follow up email"
        service.create_lead_activity(
            db_session,
            LeadActivityCreate(**activity_payload),
        )

        results = service.list_activities_by_lead(
            db_session,
            activity_payload["lead_id"],
        )

        assert len(results) == 2

    def test_update_activity(self, db_session, activity_payload):
        service = LeadActivityService()
        created = service.create_lead_activity(
            db_session,
            LeadActivityCreate(**activity_payload),
        )

        updated = service.update_lead_activity(
            db_session,
            created.id,
            LeadActivityUpdate(
                status="COMPLETED",
                outcome="INTERESTED",
            ),
        )

        assert updated is not None
        assert updated.status == ActivityStatus.COMPLETED
        assert updated.outcome == ActivityOutcome.INTERESTED

    def test_update_activity_not_found(self, db_session):
        service = LeadActivityService()
        updated = service.update_lead_activity(
            db_session,
            9999,
            LeadActivityUpdate(subject="Nope"),
        )

        assert updated is None

    def test_delete_activity(self, db_session, activity_payload):
        service = LeadActivityService()
        created = service.create_lead_activity(
            db_session,
            LeadActivityCreate(**activity_payload),
        )

        deleted = service.delete_lead_activity(
            db_session,
            created.id,
        )

        assert deleted is not None
        assert service.get_lead_activity_by_id(db_session, created.id) is None

    def test_delete_activity_not_found(self, db_session):
        service = LeadActivityService()
        deleted = service.delete_lead_activity(db_session, 9999)

        assert deleted is None