"""Rule evaluation, persistence, query bounds and real-route/JWT integration."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    ActivityOutcome, ActivityStatus, ActivityType, AvailabilityStatus, Company,
    DecisionLevel, DecisionMaker, DecisionMakerStatus, Industry, Lead, LeadActivity,
    LeadPriority, LeadScoreSnapshot, LeadStatus, MatchedBy, MoveInTimeframe, Organization,
    OrganizationStatus, OrgType, Requirement, RequirementStatus, SubscriptionTier,
    User, Warehouse, WarehouseMatch, WarehouseMatchStatus, WarehouseType,
)
from app.repositories.lead import LeadRepository
from app.repositories.lead_score_snapshot import LeadScoreSnapshotRepository
from app.services.lead_intelligence import LeadIntelligenceService, evaluate_lead
from app.services.lead_scoring_rules import SCORING_RULES, SCORING_VERSION, classify_priority
from app.schemas.lead_intelligence import LeadIntelligenceResponse, LeadNextAction


AT = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False)() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def lead(db_session):
    industry = Industry(code="LOG", name="Logistics")
    organization = Organization(
        public_id="00000000-0000-0000-0000-000000000001", org_code="INTEL",
        legal_name="Warehouse Owner", org_type=OrgType.PVT_LTD,
        subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE,
        industry=industry,
    )
    company = Company(
        company_name="Prospect", company_type="Private", industry="Manufacturing",
        organization_owners=organization,
    )
    lead = Lead(lead_number="INTEL-1", company=company)
    db_session.add(lead)
    db_session.commit()
    return lead


@pytest.fixture()
def quality_lead(db_session, lead):
    company = lead.company
    company.legal_name = "Prospect Pvt Ltd"
    company.website = "https://prospect.example.com"
    company.headquarters_city = "Bengaluru"
    company.headquarters_state = "Karnataka"
    company.products = "Industrial components"
    for index in range(2):
        db_session.add(DecisionMaker(
            company_id=company.id, full_name=f"Contact {index}", designation="Operations Director",
            decision_level=DecisionLevel.DIRECTOR, email=f"contact{index}@example.com",
            phone=f"+91987654321{index}",
        ))
    requirement = Requirement(
        lead_id=lead.id, title="Distribution warehouse", requirement_status=RequirementStatus.ACTIVE,
        required_builtup_area=50000, preferred_city="Bengaluru", budget_per_sqft=25,
        move_in_timeframe=MoveInTimeframe.IMMEDIATE, warehouse_type=WarehouseType.COVERED,
        goods_type="Industrial components",
    )
    db_session.add(requirement)
    db_session.add(LeadActivity(
        lead_id=lead.id, activity_type=ActivityType.MEETING, subject="Site discussion",
        activity_date=AT, status=ActivityStatus.COMPLETED, outcome=ActivityOutcome.INTERESTED,
        next_followup_date=AT + timedelta(days=2),
    ))
    owner = User(full_name="Owner", email="owner@example.com", hashed_password="unused")
    db_session.add(owner)
    db_session.flush()
    for index in range(2):
        warehouse = Warehouse(
            warehouse_name=f"Warehouse {index}", city="Bengaluru", state="Karnataka",
            owner_id=owner.id, availability_status=AvailabilityStatus.AVAILABLE,
        )
        db_session.add(warehouse)
        db_session.flush()
        db_session.add(WarehouseMatch(
            lead_id=lead.id, requirement_id=requirement.id, warehouse_id=warehouse.id,
            match_score=90, status=WarehouseMatchStatus.SHORTLISTED, matched_by=MatchedBy.MANUAL,
        ))
    db_session.commit()
    return lead


def score(db, lead):
    return LeadIntelligenceService().calculate_lead_score(db, lead.id)


def points(result, category):
    return sum(reason.points for reason in result.reasons if reason.factor.startswith(category + "."))


def test_minimal_lead_and_explanations(db_session, lead):
    result = score(db_session, lead)
    assert result.total_score == 10
    assert result.priority == LeadPriority.LOW
    assert result.scoring_version == SCORING_VERSION
    assert {reason.factor for reason in result.reasons} == set(SCORING_RULES)
    assert all(reason.reason and 0 <= reason.points <= reason.max_points for reason in result.reasons)
    assert sum(reason.points for reason in result.reasons) == result.total_score
    assert any(reason.points == 0 for reason in result.reasons)
    assert result.calculated_at.tzinfo == timezone.utc
    json.loads(result.model_dump_json())


def test_high_quality_lead_and_determinism(db_session, quality_lead):
    lead = LeadRepository().get_for_intelligence(db_session, quality_lead.id)
    first = evaluate_lead(lead, calculated_at=AT)
    second = evaluate_lead(lead, calculated_at=AT + timedelta(days=365))
    assert first.total_score == 100
    assert first.priority == LeadPriority.URGENT
    assert first.model_dump(exclude={"calculated_at"}) == second.model_dump(exclude={"calculated_at"})
    assert [points(first, key) for key in ("company", "decision_maker", "requirement", "activity", "warehouse_match")] == [20, 20, 30, 15, 15]
    assert sum(rule.points for rule in SCORING_RULES.values()) == 100


@pytest.mark.parametrize("value,priority", [
    (0, LeadPriority.LOW), (24, LeadPriority.LOW), (25, LeadPriority.MEDIUM),
    (49, LeadPriority.MEDIUM), (50, LeadPriority.HIGH), (74, LeadPriority.HIGH),
    (75, LeadPriority.URGENT), (100, LeadPriority.URGENT),
])
def test_priority_boundaries(value, priority):
    assert classify_priority(value) == priority


@pytest.mark.parametrize("value", [-1, 101])
def test_priority_rejects_out_of_bounds(value):
    with pytest.raises(ValueError):
        classify_priority(value)


@pytest.mark.parametrize("status", [RequirementStatus.DRAFT, RequirementStatus.CLOSED, RequirementStatus.CANCELLED, RequirementStatus.ON_HOLD])
def test_inactive_requirements_and_their_matches_do_not_score(db_session, quality_lead, status):
    quality_lead.requirements[0].requirement_status = status
    db_session.commit()
    result = score(db_session, quality_lead)
    assert points(result, "requirement") == 0
    assert points(result, "warehouse_match") == 0


def test_requirement_profiles_are_not_combined(db_session, lead):
    db_session.add_all([
        Requirement(lead_id=lead.id, title="Size only", requirement_status=RequirementStatus.ACTIVE, minimum_area=5000),
        Requirement(lead_id=lead.id, title="Location only", requirement_status=RequirementStatus.ACTIVE, preferred_city="Mumbai"),
    ])
    db_session.commit()
    assert points(score(db_session, lead), "requirement") == 13


@pytest.mark.parametrize("minimum,maximum", [(100, 10), (-1, 100), (0, 0)])
def test_invalid_requirement_area_gets_no_size_points(db_session, lead, minimum, maximum):
    db_session.add(Requirement(
        lead_id=lead.id, title="Area", requirement_status=RequirementStatus.ACTIVE,
        minimum_area=minimum, maximum_area=maximum,
    ))
    db_session.commit()
    assert points(score(db_session, lead), "requirement") == 5


def test_contacts_are_not_combined_and_disqualified_contacts_excluded(db_session, lead):
    db_session.add_all([
        DecisionMaker(company_id=lead.company_id, full_name="Email", designation=" ", email="a@example.com"),
        DecisionMaker(company_id=lead.company_id, full_name="Phone", designation=" ", phone="1234567890"),
        DecisionMaker(company_id=lead.company_id, full_name="Excluded", designation="Director",
                      decision_level=DecisionLevel.DIRECTOR, email="b@example.com", phone="123",
                      decision_maker_status=DecisionMakerStatus.DISQUALIFIED),
    ])
    db_session.commit()
    assert points(score(db_session, lead), "decision_maker") == 12


def test_foreign_company_primary_contact_is_not_scored(db_session, lead):
    other = Company(company_name="Other", industry="Other", company_type="Private", organization_id=lead.company.organization_id)
    contact = DecisionMaker(company=other, full_name="Foreign", designation="Director",
                            decision_level=DecisionLevel.DIRECTOR, email="foreign@example.com", phone="123")
    db_session.add(contact)
    db_session.flush()
    lead.primary_decision_maker_id = contact.id
    db_session.commit()
    assert points(score(db_session, lead), "decision_maker") == 0


def test_latest_negative_outcome_overrides_older_positive(db_session, quality_lead):
    db_session.add(LeadActivity(
        lead_id=quality_lead.id, activity_type=ActivityType.CALL, subject="Declined",
        activity_date=AT + timedelta(days=1), status=ActivityStatus.COMPLETED,
        outcome=ActivityOutcome.NOT_INTERESTED,
    ))
    db_session.commit()
    assert points(score(db_session, quality_lead), "activity") == 11


@pytest.mark.parametrize("status", [ActivityStatus.SCHEDULED, ActivityStatus.CANCELLED])
def test_uncompleted_activities_do_not_imply_engagement(db_session, lead, status):
    db_session.add(LeadActivity(
        lead_id=lead.id, activity_type=ActivityType.CALL, subject="Call", activity_date=AT,
        status=status, outcome=ActivityOutcome.INTERESTED,
    ))
    db_session.commit()
    assert points(score(db_session, lead), "activity") == 0


@pytest.mark.parametrize("status", [WarehouseMatchStatus.REJECTED, WarehouseMatchStatus.STALE, WarehouseMatchStatus.CONVERTED])
def test_nonviable_matches_excluded(db_session, quality_lead, status):
    for match in quality_lead.warehouse_matches:
        match.status = status
    db_session.commit()
    assert points(score(db_session, quality_lead), "warehouse_match") == 0


@pytest.mark.parametrize("match_score,expected", [(49, 0), (50, 8), (79, 8), (80, 15), (100, 15)])
def test_match_score_thresholds(db_session, quality_lead, match_score, expected):
    for match in quality_lead.warehouse_matches:
        match.match_score = match_score
    db_session.commit()
    assert points(score(db_session, quality_lead), "warehouse_match") == expected


def test_unavailable_warehouses_excluded(db_session, quality_lead):
    for match in quality_lead.warehouse_matches:
        match.warehouse.availability_status = AvailabilityStatus.OCCUPIED
    db_session.commit()
    assert points(score(db_session, quality_lead), "warehouse_match") == 0


def test_multiple_matches_require_distinct_warehouses(db_session, quality_lead):
    matches = quality_lead.warehouse_matches
    matches[1].requirement_id = None
    matches[1].warehouse_id = matches[0].warehouse_id
    db_session.commit()
    assert points(score(db_session, quality_lead), "warehouse_match") == 12


def test_whitespace_is_not_profile_information(db_session, lead):
    lead.company.website = "  "
    lead.company.products = "\t"
    db_session.commit()
    assert score(db_session, lead).total_score == 10


def test_read_and_snapshot_do_not_change_lead(db_session, lead):
    before = {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}
    service = LeadIntelligenceService()
    service.calculate_lead_score(db_session, lead.id)
    assert service.list_score_history(db_session, lead.id) == []
    service.create_score_snapshot(db_session, lead.id)
    db_session.refresh(lead)
    assert before == {column.name: getattr(lead, column.name) for column in Lead.__table__.columns}
    assert len(lead.score_snapshots) == 1


def test_history_preserves_versions_and_pagination(db_session, lead):
    service = LeadIntelligenceService()
    first = service.create_score_snapshot(db_session, lead.id)
    old = db_session.scalars(select(LeadScoreSnapshot)).one()
    # Simulate a snapshot from a previous algorithm; recalculation must not rewrite it.
    old.scoring_version = "legacy"
    db_session.commit()
    lead.company.website = "https://example.com"
    db_session.commit()
    second = service.create_score_snapshot(db_session, lead.id)
    history = service.list_score_history(db_session, lead.id)
    assert [item.scoring_version for item in history] == [SCORING_VERSION, "legacy"]
    assert history[1].total_score == first.total_score
    assert history[1].reasons == first.reasons
    assert second.total_score == first.total_score + 3
    assert service.list_score_history(db_session, lead.id, limit=1, offset=1) == history[1:]
    assert service.list_score_history(db_session, lead.id, offset=10) == []


def test_tied_history_timestamps_have_stable_order(db_session, lead):
    for version in ("first", "second", "third"):
        db_session.add(LeadScoreSnapshot(
            lead_id=lead.id, total_score=0, priority=LeadPriority.LOW, scoring_version=version,
            calculated_at=AT, reasons=[{"factor": "test", "points": 0, "max_points": 0, "reason": "Historical test"}],
        ))
    db_session.commit()
    assert [item.scoring_version for item in LeadIntelligenceService().list_score_history(db_session, lead.id)] == ["third", "second", "first"]


@pytest.mark.parametrize("orm_delete", [True, False])
def test_lead_deletion_cascades_snapshots(db_session, lead, orm_delete):
    LeadIntelligenceService().create_score_snapshot(db_session, lead.id)
    if orm_delete:
        db_session.delete(lead)
    else:
        db_session.execute(delete(Lead).where(Lead.id == lead.id))
    db_session.commit()
    assert db_session.scalars(select(LeadScoreSnapshot)).all() == []


@pytest.mark.parametrize("value", [-1, 101])
def test_database_score_constraint(db_session, lead, value):
    db_session.add(LeadScoreSnapshot(
        lead_id=lead.id, total_score=value, priority=LeadPriority.LOW,
        scoring_version=SCORING_VERSION, reasons=[], calculated_at=AT,
    ))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_pending_edits_are_not_committed(db_session, lead):
    lead.company.notes = "Uncommitted"
    with pytest.raises(ValueError, match="pending changes"):
        LeadIntelligenceService().create_score_snapshot(db_session, lead.id)
    db_session.rollback()
    assert lead.company.notes is None


def test_snapshot_repository_rolls_back_failed_insert(db_session, lead):
    snapshot = LeadScoreSnapshot(
        lead_id=lead.id, total_score=101, priority=LeadPriority.LOW,
        scoring_version=SCORING_VERSION, reasons=[], calculated_at=AT,
    )
    with pytest.raises(IntegrityError):
        LeadScoreSnapshotRepository().create(db_session, snapshot)
    assert db_session.is_active
    assert LeadIntelligenceService().list_score_history(db_session, lead.id) == []
    assert LeadIntelligenceService().create_score_snapshot(db_session, lead.id).total_score == 10


def test_read_never_autoflushes_unrelated_pending_changes(db_session, lead):
    lead_id = lead.id
    # Invalid unrelated row would fail immediately if a scoring read flushed it.
    pending = User(email="incomplete@example.com")
    db_session.add(pending)
    db_session.autoflush = True
    assert LeadIntelligenceService().calculate_lead_score(db_session, lead_id).total_score == 10
    assert pending.id is None
    assert pending in db_session.new
    db_session.rollback()


def test_history_and_matches_are_scoped_to_lead(db_session, quality_lead):
    other = Lead(lead_number="OTHER", company_id=quality_lead.company_id)
    db_session.add(other)
    db_session.flush()
    requirement = Requirement(
        lead_id=other.id, title="Other lead's requirement", requirement_status=RequirementStatus.ACTIVE,
    )
    db_session.add(requirement)
    db_session.flush()
    for match in quality_lead.warehouse_matches:
        match.requirement_id = requirement.id
    db_session.commit()
    service = LeadIntelligenceService()
    assert points(score(db_session, quality_lead), "warehouse_match") == 0
    service.create_score_snapshot(db_session, quality_lead.id)
    assert service.list_score_history(db_session, other.id) == []
    assert service.list_score_history(db_session, 99999) is None


def test_many_rows_do_not_inflate_score(db_session, quality_lead):
    for index in range(25):
        db_session.add(DecisionMaker(
            company_id=quality_lead.company_id, full_name=f"Additional {index}",
            designation="Director", decision_level=DecisionLevel.DIRECTOR,
            email=f"extra{index}@example.com", phone="1234567890",
        ))
        db_session.add(Requirement(
            lead_id=quality_lead.id, title=f"Additional {index}", requirement_status=RequirementStatus.ACTIVE,
            required_builtup_area=10000, preferred_city="Mumbai", budget_per_sqft=30,
            move_in_timeframe=MoveInTimeframe.IMMEDIATE, warehouse_type=WarehouseType.COVERED,
            goods_type="Components",
        ))
    db_session.commit()
    result = score(db_session, quality_lead)
    assert result.total_score == 100
    assert sum(reason.points for reason in result.reasons) == 100


def test_equal_profile_scores_select_lowest_id(db_session, lead):
    contacts = [DecisionMaker(company_id=lead.company_id, full_name=name, designation="Manager")
                for name in ("First", "Second")]
    requirements = [Requirement(lead_id=lead.id, title=name, requirement_status=RequirementStatus.ACTIVE)
                    for name in ("First", "Second")]
    db_session.add_all(contacts + requirements)
    db_session.commit()
    result = score(db_session, lead)
    contact_id = min(contact.id for contact in contacts)
    requirement_id = min(requirement.id for requirement in requirements)
    assert all(f"Selected decision maker: {contact_id}." in reason.reason
               for reason in result.reasons if reason.factor.startswith("decision_maker.")
               and reason.factor != "decision_maker.multiple")
    assert all(f"Selected requirement: {requirement_id}." in reason.reason
               for reason in result.reasons if reason.factor.startswith("requirement."))


def test_query_count_and_no_lazy_queries_during_evaluation(db_session, quality_lead):
    lead_id = quality_lead.id
    db_session.expunge_all()
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", capture)
    try:
        loaded = LeadRepository().get_for_intelligence(db_session, lead_id)
        assert len(statements) == 5
        result = evaluate_lead(loaded, calculated_at=AT)
        assert result.total_score == 100
        assert len(statements) == 5
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture)


@pytest.fixture()
def client(db_session):
    previous = app.dependency_overrides.copy()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture()
def headers(db_session):
    user = User(full_name="Admin", email="admin@example.com", hashed_password="unused", role="admin")
    db_session.add(user)
    db_session.commit()
    return {"Authorization": "Bearer " + create_access_token({"sub": user.email})}


def test_api_current_calculate_and_history(client, headers, quality_lead):
    path = f"/leads/{quality_lead.id}/intelligence"
    assert client.get(path + "/history", headers=headers).json() == []
    current = client.get(path, headers=headers)
    assert current.status_code == 200
    assert current.json()["total_score"] == 100
    assert client.get(path + "/history", headers=headers).json() == []
    saved = client.post(path + "/calculate", headers=headers)
    assert saved.status_code == 200, saved.text
    assert "id" not in saved.json()
    assert saved.json()["priority"] == "URGENT"
    history = client.get(path + "/history?limit=1&offset=0", headers=headers)
    assert history.json() == [saved.json()]
    assert client.get(path + "/history?offset=1", headers=headers).json() == []


@pytest.mark.parametrize("method,suffix", [("get", ""), ("get", "/history"), ("post", "/calculate")])
def test_api_missing_lead(client, headers, method, suffix):
    response = getattr(client, method)("/leads/99999/intelligence" + suffix, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found"


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=bad"])
def test_api_pagination_validation(client, headers, lead, query):
    assert client.get(f"/leads/{lead.id}/intelligence/history?{query}", headers=headers).status_code == 422


@pytest.mark.parametrize("method,suffix", [("get", ""), ("get", "/history"), ("post", "/calculate")])
@pytest.mark.parametrize("auth", ["missing", "invalid", "expired", "inactive"])
def test_api_authentication(client, db_session, lead, method, suffix, auth):
    headers = {}
    if auth == "invalid":
        headers = {"Authorization": "Bearer invalid"}
    elif auth in {"expired", "inactive"}:
        db_session.add(User(full_name="User", email="auth@example.com", hashed_password="unused", role="admin", is_active=auth != "inactive"))
        db_session.commit()
        token = create_access_token({"sub": "auth@example.com"}, expires_delta=timedelta(seconds=-10) if auth == "expired" else None)
        headers = {"Authorization": f"Bearer {token}"}
    assert getattr(client, method)(f"/leads/{lead.id}/intelligence{suffix}", headers=headers).status_code == 401


def test_nonadmin_reads_but_cannot_persist(client, db_session, lead):
    db_session.add(User(full_name="Reader", email="reader@example.com", hashed_password="unused", role="user"))
    db_session.commit()
    headers = {"Authorization": "Bearer " + create_access_token({"sub": "reader@example.com"})}
    path = f"/leads/{lead.id}/intelligence"
    assert client.get(path, headers=headers).status_code == 200
    assert client.get(path + "/history", headers=headers).status_code == 200
    assert client.get("/leads/prioritized", headers=headers).status_code == 200
    assert client.post(path + "/calculate", headers=headers).status_code == 403
    assert db_session.scalars(select(LeadScoreSnapshot)).all() == []


def test_phase2_component_summaries_and_match_evidence(db_session, quality_lead):
    result = score(db_session, quality_lead)
    assert {key: value.score for key, value in result.component_scores.items()} == {
        "company": 20, "decision_maker": 20, "requirement": 30, "activity": 15, "warehouse_match": 15,
    }
    assert sum(value.max_score for value in result.component_scores.values()) == 100
    assert len(result.positive_signals) == 25
    assert result.scoring_gaps == []
    assert result.explanation.missing_information == []
    assert result.explanation.recommended_action == LeadNextAction.FOLLOW_UP
    assert not result.explanation.research_required
    assert "not represented" in result.explanation.limitations[0]
    best = min(quality_lead.warehouse_matches, key=lambda match: (-match.match_score, match.id))
    evidence = result.explanation.best_warehouse_match
    assert evidence.match_id == best.id
    assert evidence.match_score == float(best.match_score)
    assert evidence.requirement_id == best.requirement_id


@pytest.mark.parametrize("scenario,expected", [
    ("company", LeadNextAction.RESEARCH_COMPANY),
    ("contact", LeadNextAction.FIND_DECISION_MAKER),
    ("contact_details", LeadNextAction.RESEARCH_CONTACT),
    ("contact_role", LeadNextAction.RESEARCH_CONTACT),
    ("requirement", LeadNextAction.REVIEW_REQUIREMENT),
    ("size", LeadNextAction.REVIEW_REQUIREMENT),
    ("location", LeadNextAction.REVIEW_REQUIREMENT),
    ("match", LeadNextAction.FIND_WAREHOUSE_MATCH),
    ("outreach", LeadNextAction.CONTACT_DECISION_MAKER),
    ("engagement", LeadNextAction.FOLLOW_UP),
    ("negative", LeadNextAction.MONITOR),
    ("bounced", LeadNextAction.RESEARCH_CONTACT),
    ("neutral", LeadNextAction.MONITOR),
])
def test_phase2_action_policy(db_session, quality_lead, scenario, expected):
    loaded = LeadRepository().get_for_intelligence(db_session, quality_lead.id)
    if scenario == "company":
        loaded.company.industry = "  "
    elif scenario == "contact":
        for contact in loaded.company.decision_makers:
            contact.decision_maker_status = DecisionMakerStatus.DISQUALIFIED
    elif scenario == "contact_details":
        for contact in loaded.company.decision_makers:
            contact.email = contact.phone = None
    elif scenario == "contact_role":
        for contact in loaded.company.decision_makers:
            contact.decision_level = DecisionLevel.OTHER
    elif scenario == "requirement":
        loaded.requirements[0].requirement_status = RequirementStatus.CLOSED
    elif scenario == "size":
        loaded.requirements[0].required_builtup_area = None
    elif scenario == "location":
        loaded.requirements[0].preferred_city = None
    elif scenario == "match":
        for match in loaded.warehouse_matches:
            match.status = WarehouseMatchStatus.REJECTED
    elif scenario == "outreach":
        for activity in loaded.activities:
            activity.status = ActivityStatus.CANCELLED
    elif scenario in {"negative", "bounced", "neutral"}:
        for activity in loaded.activities:
            activity.outcome = {
                "negative": ActivityOutcome.NOT_INTERESTED,
                "bounced": ActivityOutcome.BOUNCED,
                "neutral": ActivityOutcome.NO_ANSWER,
            }[scenario]
            if scenario == "neutral":
                activity.next_followup_date = None
    result = evaluate_lead(loaded, calculated_at=AT)
    assert result.explanation.recommended_action == expected
    assert result.explanation.action_reason
    assert result.explanation.action_version == "v1"
    assert result == evaluate_lead(loaded, calculated_at=AT)
    db_session.rollback()


@pytest.mark.parametrize("status", [LeadStatus.WON, LeadStatus.LOST, LeadStatus.DISQUALIFIED, LeadStatus.DORMANT])
def test_phase2_closed_and_dormant_leads_do_not_prompt_outreach(db_session, quality_lead, status):
    loaded = LeadRepository().get_for_intelligence(db_session, quality_lead.id)
    loaded.status = status
    result = evaluate_lead(loaded, calculated_at=AT)
    assert result.total_score == 100  # Workflow is independent of evidence quality.
    assert result.explanation.recommended_action == LeadNextAction.MONITOR
    assert status.value in result.explanation.action_reason
    db_session.rollback()


def test_phase2_missing_timeline_is_not_flexible_timeline(db_session, quality_lead):
    loaded = LeadRepository().get_for_intelligence(db_session, quality_lead.id)
    loaded.requirements[0].move_in_timeframe = MoveInTimeframe.FLEXIBLE
    flexible = evaluate_lead(loaded, calculated_at=AT)
    assert not any("timeline" in message for message in flexible.explanation.missing_information)
    assert any("move-in" in message for message in flexible.scoring_gaps)
    loaded.requirements[0].move_in_timeframe = None
    missing = evaluate_lead(loaded, calculated_at=AT)
    assert any("timeline" in message for message in missing.explanation.missing_information)
    assert missing.total_score == flexible.total_score
    db_session.rollback()


def test_phase2_history_keeps_action_and_match_evidence(db_session, quality_lead):
    service = LeadIntelligenceService()
    first = service.create_score_snapshot(db_session, quality_lead.id)
    original = db_session.scalars(select(LeadScoreSnapshot)).one()
    original_json = json.dumps(original.reasons, sort_keys=True)
    quality_lead.status = LeadStatus.LOST
    for match in quality_lead.warehouse_matches:
        match.match_score = 5
    db_session.commit()
    second = service.create_score_snapshot(db_session, quality_lead.id)
    assert second.explanation.recommended_action == LeadNextAction.MONITOR
    history = service.list_score_history(db_session, quality_lead.id)
    assert history == [second, first]
    assert history[1].explanation.best_warehouse_match is not None
    db_session.refresh(original)
    assert json.dumps(original.reasons, sort_keys=True) == original_json


def test_phase2_legacy_snapshot_has_no_invented_action(db_session, lead):
    result = score(db_session, lead)
    legacy_reasons = [reason.model_dump(exclude={"context"}) for reason in result.reasons]
    snapshot = LeadScoreSnapshot(
        lead_id=lead.id, total_score=result.total_score, priority=result.priority,
        scoring_version="v1", reasons=legacy_reasons, calculated_at=AT,
    )
    db_session.add(snapshot)
    db_session.commit()
    legacy = LeadIntelligenceResponse.model_validate(snapshot)
    assert legacy.explanation is None
    assert legacy.component_scores == result.component_scores
    assert legacy.positive_signals == result.positive_signals
    assert snapshot.reasons == legacy_reasons


def test_phase2_pipeline_order_pagination_filters_and_no_writes(db_session, quality_lead):
    company = Company(
        company_name="Research Prospect", company_type="Private", industry="Retail",
        organization_id=quality_lead.company.organization_id,
    )
    others = [Lead(lead_number=f"PIPE-{index}", company=company, priority=LeadPriority.URGENT)
              for index in range(3)]
    db_session.add_all(others)
    db_session.commit()
    service = LeadIntelligenceService()
    result = service.list_prioritized_leads(db_session)
    ids = [quality_lead.id] + [item.id for item in others]
    assert [item.lead_id for item in result.items] == ids
    assert result.total == 4
    assert all(item.intelligence.calculated_at == result.calculated_at for item in result.items)
    page = service.list_prioritized_leads(db_session, limit=2, offset=1)
    assert [item.lead_id for item in page.items] == ids[1:3]
    assert page.total == 4
    assert service.list_prioritized_leads(db_session, offset=99).items == []
    for filters, expected_ids in [
        ({"priority": LeadPriority.URGENT}, ids[:1]),
        ({"minimum_score": 99}, ids[:1]),
        ({"industry": "Retail"}, ids[1:]),
        ({"industry": "retail"}, []),
        ({"organization_id": company.organization_id}, ids),
        ({"organization_id": 99999}, []),
        ({"has_active_requirement": True}, ids[:1]),
        ({"has_active_requirement": False}, ids[1:]),
        ({"research_required": True}, ids[1:]),
        ({"research_required": False}, ids[:1]),
        ({"industry": "Retail", "minimum_score": 99}, []),
    ]:
        filtered = service.list_prioritized_leads(db_session, **filters)
        assert [item.lead_id for item in filtered.items] == expected_ids
        assert filtered.total == len(expected_ids)
    assert db_session.scalars(select(LeadScoreSnapshot)).all() == []
    assert all(item.priority == LeadPriority.URGENT for item in others)
    others[0].status = LeadStatus.LOST
    db_session.commit()
    assert service.list_prioritized_leads(db_session).total == 3
    closed = service.list_prioritized_leads(db_session, status=LeadStatus.LOST)
    assert closed.total == 1
    assert closed.items[0].intelligence.explanation.recommended_action == LeadNextAction.MONITOR


def test_phase2_pipeline_scores_current_data_not_latest_snapshot(db_session, lead):
    service = LeadIntelligenceService()
    old = service.create_score_snapshot(db_session, lead.id)
    lead.company.website = "https://example.com"
    db_session.commit()
    current = service.list_prioritized_leads(db_session).items[0].intelligence
    assert current.total_score == old.total_score + 3
    assert service.list_score_history(db_session, lead.id) == [old]


def test_phase2_pipeline_batched_queries_and_heap_replacement(db_session, lead):
    rows = [Lead(lead_number=f"BATCH-{index}", company_id=lead.company_id) for index in range(104)]
    db_session.add_all(rows)
    db_session.flush()
    last_id = rows[-1].id
    db_session.add(Requirement(lead_id=last_id, title="Active", requirement_status=RequirementStatus.ACTIVE))
    db_session.commit()
    db_session.expunge_all()
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", capture)
    try:
        result = LeadIntelligenceService().list_prioritized_leads(db_session, limit=1)
        assert result.total == 105
        assert result.items[0].lead_id == last_id
        assert len(statements) == 10  # Five SELECTs per batch, no per-lead lazy reads.
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture)


@pytest.mark.parametrize("query", [
    "limit=0", "limit=101", "offset=-1", "offset=10001", "minimum_score=-1",
    "minimum_score=101", "priority=HOT", "organization_id=0", "industry=",
    "has_active_requirement=bad", "research_required=bad", "status=bad",
])
def test_phase2_pipeline_validation(client, headers, query):
    assert client.get(f"/leads/prioritized?{query}", headers=headers).status_code == 422


@pytest.mark.parametrize("auth", ["missing", "invalid", "expired", "inactive"])
def test_phase2_pipeline_authentication(client, db_session, auth):
    headers = {}
    if auth == "invalid":
        headers = {"Authorization": "Bearer invalid"}
    elif auth in {"expired", "inactive"}:
        user = User(full_name="Reader", email="pipeline@example.com", hashed_password="unused",
                    role="user", is_active=auth != "inactive")
        db_session.add(user)
        db_session.commit()
        token = create_access_token({"sub": user.email}, expires_delta=timedelta(seconds=-10) if auth == "expired" else None)
        headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/leads/prioritized", headers=headers).status_code == 401


def test_phase2_pipeline_api_and_existing_route_resolution(client, headers, quality_lead):
    response = client.get("/leads/prioritized?priority=URGENT&minimum_score=80&has_active_requirement=true", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["lead_id"] == quality_lead.id
    assert data["items"][0]["intelligence"]["explanation"]["recommended_action"] == "FOLLOW_UP"
    assert client.get(f"/leads/{quality_lead.id}", headers=headers).status_code == 200
    assert client.get(f"/leads/company/{quality_lead.company_id}", headers=headers).status_code == 200
    assert client.get(f"/leads/{quality_lead.id}/intelligence", headers=headers).status_code == 200


def test_phase2_orphaned_company_is_safe_and_requires_research():
    # A corrupt/legacy graph is evaluated safely; no invalid FK is inserted.
    orphan = Lead(id=999, company_id=999, lead_number="ORPHAN", status=LeadStatus.NEW)
    orphan.company = None
    result = evaluate_lead(orphan, calculated_at=AT)
    assert result.total_score == 0
    assert result.priority == LeadPriority.LOW
    assert result.explanation.recommended_action == LeadNextAction.RESEARCH_COMPANY
    assert result.explanation.selected_decision_maker_id is None
    assert result.explanation.best_warehouse_match is None
    assert "Associated company is missing." in result.explanation.missing_information


def test_phase2_best_match_evidence_is_copied_without_interpreting_claims(db_session, quality_lead):
    loaded = LeadRepository().get_for_intelligence(db_session, quality_lead.id)
    for match in loaded.warehouse_matches:
        match.match_score = 88
    best = min(loaded.warehouse_matches, key=lambda match: match.id)
    best.model_version = "warehouse-rules-v1"
    best.requirement_compatibility = "Recorded manual assessment; requires review"
    best.match_reasons = '[{"factor":"capacity","points":40}]'
    best.concern_reasons = '["Fire compliance not evaluated"]'
    result = evaluate_lead(loaded, calculated_at=AT)
    evidence = result.explanation.best_warehouse_match
    assert evidence.match_id == best.id
    assert evidence.model_version == best.model_version
    assert evidence.requirement_compatibility == best.requirement_compatibility
    assert evidence.match_reasons == best.match_reasons
    assert evidence.concern_reasons == best.concern_reasons
    best.status = WarehouseMatchStatus.STALE
    new_result = evaluate_lead(loaded, calculated_at=AT)
    assert new_result.explanation.best_warehouse_match.match_id != best.id
    assert result.explanation.best_warehouse_match.match_id == best.id
    db_session.rollback()


def test_snapshot_model_import_and_mappers_in_fresh_interpreter():
    # A fresh registry catches import-order problems hidden by app.main imports.
    code = """
import app.models.lead_score_snapshot as snapshot_module
from app.models.lead import Lead
from sqlalchemy.orm import configure_mappers

configure_mappers()
Snapshot = snapshot_module.LeadScoreSnapshot
assert 'Lead' not in vars(snapshot_module)  # TYPE_CHECKING only, not a runtime import
assert Snapshot.lead.property.mapper.class_ is Lead
assert Snapshot.lead.property.back_populates == 'score_snapshots'
assert Lead.score_snapshots.property.mapper.class_ is Snapshot
assert Lead.score_snapshots.property.back_populates == 'lead'
assert next(iter(Snapshot.__table__.c.lead_id.foreign_keys)).target_fullname == 'leads.id'
"""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_snapshot_relationship_and_complete_result_round_trip(db_session, quality_lead):
    service = LeadIntelligenceService()
    saved = service.create_score_snapshot(db_session, quality_lead.id)
    snapshot = db_session.scalars(select(LeadScoreSnapshot)).one()
    assert snapshot.lead is quality_lead
    assert snapshot in quality_lead.score_snapshots
    assert snapshot.scoring_version == SCORING_VERSION == "v1"
    assert snapshot.reasons == [reason.model_dump(mode="json") for reason in saved.reasons]
    assert len(snapshot.reasons) == 25
    assert sum(reason["points"] for reason in snapshot.reasons) == snapshot.total_score
    expected = saved.model_dump(mode="json")
    lead_id = quality_lead.id
    db_session.expunge_all()
    assert service.list_score_history(db_session, lead_id)[0].model_dump(mode="json") == expected


def test_snapshot_history_does_not_depend_on_current_policy(db_session, quality_lead, monkeypatch):
    import app.services.lead_intelligence as intelligence

    service = LeadIntelligenceService()
    lead_id = quality_lead.id
    saved = service.create_score_snapshot(db_session, lead_id).model_dump(mode="json")

    def forbidden_evaluation(*args, **kwargs):
        pytest.fail("Reading history must never evaluate today's scoring policy")

    monkeypatch.setattr(intelligence, "evaluate_lead", forbidden_evaluation)
    monkeypatch.setattr(intelligence, "SCORING_VERSION", "future-test-version")
    monkeypatch.setattr(intelligence, "SCORING_RULES", {})
    db_session.expunge_all()
    history = service.list_score_history(db_session, lead_id)
    assert [item.model_dump(mode="json") for item in history] == [saved]


@pytest.mark.parametrize("method", ["calculate_lead_score", "create_score_snapshot", "list_score_history"])
def test_snapshot_workflow_missing_lead_has_no_writes(db_session, method):
    assert getattr(LeadIntelligenceService(), method)(db_session, 99999) is None
    assert db_session.scalars(select(LeadScoreSnapshot)).all() == []
    assert not db_session.new and not db_session.dirty and not db_session.deleted


@pytest.mark.parametrize("limit,offset", [(0, 0), (101, 0), (1, -1)])
def test_snapshot_history_service_rejects_invalid_pagination(db_session, lead, limit, offset):
    with pytest.raises(ValueError, match="limit must be 1-100"):
        LeadIntelligenceService().list_score_history(db_session, lead.id, limit=limit, offset=offset)


def test_snapshot_api_repeated_reads_and_explicit_appends(client, headers, quality_lead):
    path = f"/leads/{quality_lead.id}/intelligence"
    for _ in range(3):
        response = client.get(path, headers=headers)
        assert response.status_code == 200
    assert client.get(path + "/history", headers=headers).json() == []

    snapshots = []
    for _ in range(2):
        response = client.post(path + "/calculate", headers=headers)
        assert response.status_code == 200
        snapshots.append(response.json())
    assert snapshots[0]["reasons"] == snapshots[1]["reasons"]
    assert snapshots[0]["total_score"] == snapshots[1]["total_score"] == 100
    assert snapshots[0]["scoring_version"] == snapshots[1]["scoring_version"] == SCORING_VERSION
    history = client.get(path + "/history", headers=headers)
    assert history.status_code == 200
    assert history.json() == snapshots[::-1]
    assert client.get(path + "/history?limit=1&offset=1", headers=headers).json() == snapshots[:1]
    assert client.get(path, headers=headers).status_code == 200
    assert client.get(path + "/history", headers=headers).json() == snapshots[::-1]