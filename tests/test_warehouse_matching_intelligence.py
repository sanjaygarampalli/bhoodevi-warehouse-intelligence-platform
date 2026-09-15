"""Deterministic matching, workflow preservation, bounded queries and real JWT API."""
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    AvailabilityStatus, Company, Lead, MatchedBy, Organization, OrganizationMemberRole,
    OrganizationMembership, OrganizationStatus, OrgType, Requirement, RequirementStatus,
    SubscriptionTier, User, Warehouse, WarehouseMatch, WarehouseMatchStatus, WarehouseType,
)
from app.services.warehouse_match import WarehouseMatchService, evaluate_warehouse_match
from app.services.warehouse_matching_rules import WEIGHTS, classify_match


def requirement(**changes):
    values = dict(id=1, lead_id=1, title="Distribution space", preferred_city="Bengaluru",
                  preferred_state="Karnataka", preferred_pincode="560001", minimum_area=1000,
                  required_builtup_area=800, required_open_area=200, maximum_area=2000,
                  warehouse_type=WarehouseType.COVERED, requirement_status=RequirementStatus.ACTIVE)
    values.update(changes)
    return Requirement(**values)


def warehouse(**changes):
    values = dict(id=1, warehouse_name="Central warehouse", owner_id=1, city="Bengaluru",
                  state="Karnataka", postal_code="560001", total_area_sqft=1000,
                  built_up_area_sqft=800, open_area_sqft=200,
                  warehouse_type=WarehouseType.COVERED, availability_status=AvailabilityStatus.AVAILABLE)
    values.update(changes)
    return Warehouse(**values)


def points(result, factor):
    return next(reason.points for reason in result.reasons if reason.factor == factor)


def assert_explainable(result):
    assert 0 <= result.match_score <= 100
    assert result.match_level == classify_match(result.match_score)
    assert {reason.factor for reason in result.reasons} == set(WEIGHTS)
    assert sum(reason.maximum_points for reason in result.reasons) == 100
    assert sum(reason.points for reason in result.reasons) + sum(a.points for a in result.adjustments) == result.match_score
    for reason in result.reasons:
        assert 0 <= reason.points <= reason.maximum_points
        assert len(reason.explanation) > 15
    for adjustment in result.adjustments:
        assert adjustment.explanation in result.warnings


def test_excellent_and_pure_determinism():
    req, stock = requirement(), warehouse()
    before = dict(req.__dict__), dict(stock.__dict__)
    first = evaluate_warehouse_match(req, stock)
    assert first.match_score == 100
    assert first.match_level == "EXCELLENT"
    assert first.warnings == []
    assert first == evaluate_warehouse_match(req, stock)
    assert before == (req.__dict__, stock.__dict__)
    assert_explainable(first)


def test_minimal_requirement_is_not_confused_with_high_suitability():
    result = evaluate_warehouse_match(Requirement(id=1, lead_id=1, title="Minimal"), warehouse())
    assert result.match_score == 20
    assert result.match_level == "POOR"
    assert points(result, "capacity") == points(result, "location") == points(result, "type") == 0
    assert_explainable(result)


@pytest.mark.parametrize("changes", [
    {"total_area_sqft": 999}, {"built_up_area_sqft": 799}, {"open_area_sqft": 199},
    {"total_area_sqft": 0}, {"built_up_area_sqft": Decimal("0.01")},
])
def test_capacity_failure_is_poor(changes):
    result = evaluate_warehouse_match(requirement(), warehouse(**changes))
    assert points(result, "capacity") == 0
    assert result.match_score == 39
    assert result.match_level == "POOR"
    assert any("below the required minimum" in warning for warning in result.warnings)
    assert_explainable(result)


def test_component_demand_cannot_exceed_known_total():
    result = evaluate_warehouse_match(requirement(minimum_area=None), warehouse(total_area_sqft=999))
    assert result.match_score == 39
    assert any("combined" in warning for warning in result.warnings)


@pytest.mark.parametrize("changes", [
    {"minimum_area": -1}, {"minimum_area": 0}, {"maximum_area": 0},
    {"minimum_area": 3000}, {"maximum_area": 999}, {"required_open_area": -1},
    {"minimum_area": Decimal("NaN")}, {"maximum_area": Decimal("Infinity")},
])
def test_invalid_requirement_area_is_safe_and_not_excellent(changes):
    result = evaluate_warehouse_match(requirement(**changes), warehouse())
    assert result.match_score == 39
    assert any("Invalid requirement area" in warning for warning in result.warnings)
    assert_explainable(result)


@pytest.mark.parametrize("field", ["total_area_sqft", "built_up_area_sqft", "open_area_sqft"])
@pytest.mark.parametrize("value", [None, -1, Decimal("NaN")])
def test_missing_or_invalid_warehouse_capacity_not_awarded(field, value):
    result = evaluate_warehouse_match(requirement(), warehouse(**{field: value}))
    assert points(result, "capacity") == 0
    assert result.match_score == 65
    assert any("capacity" in warning for warning in result.warnings)
    assert_explainable(result)


@pytest.mark.parametrize("changes,expected", [
    ({"total_area_sqft": 1500}, 35),
    ({"total_area_sqft": 2000}, 35),
    ({"total_area_sqft": 2001}, 25),
    ({"built_up_area_sqft": 2000, "total_area_sqft": 2200}, 25),
])
def test_sufficient_and_oversized_area(changes, expected):
    result = evaluate_warehouse_match(requirement(), warehouse(**changes))
    assert points(result, "capacity") == expected
    assert_explainable(result)


def test_total_is_not_substituted_for_builtup():
    result = evaluate_warehouse_match(requirement(), warehouse(total_area_sqft=10000, built_up_area_sqft=None))
    assert points(result, "capacity") == 0


def test_missing_total_with_maximum_and_component_demand_is_unknown():
    result = evaluate_warehouse_match(requirement(minimum_area=None), warehouse(total_area_sqft=None))
    assert points(result, "capacity") == 0
    assert "Requested maximum area cannot be verified." in result.warnings


def test_zero_optional_component_demand_does_not_require_that_component():
    result = evaluate_warehouse_match(requirement(required_open_area=0), warehouse(open_area_sqft=None))
    assert result.match_score == 100


def test_unknown_requested_type_is_not_excellent():
    result = evaluate_warehouse_match(requirement(), warehouse(warehouse_type=None))
    assert result.match_score == 79
    assert_explainable(result)


def test_maximum_only_is_not_evidence_of_sufficient_capacity():
    result = evaluate_warehouse_match(requirement(minimum_area=None, required_builtup_area=None, required_open_area=None), warehouse())
    assert points(result, "capacity") == 0


@pytest.mark.parametrize("changes,expected", [
    ({"city": "  BENGALURU  ", "state": "karnataka"}, 30),
    ({"postal_code": "560002"}, 20),
    ({"city": "Mysuru", "postal_code": "570001"}, 10),
    ({"state": "Maharashtra"}, 0),
    ({"city": "Mumbai", "state": "Maharashtra", "postal_code": "400001"}, 0),
    ({"postal_code": None}, 20),
])
def test_location_comparisons(changes, expected):
    result = evaluate_warehouse_match(requirement(), warehouse(**changes))
    assert points(result, "location") == expected
    if expected < 30:
        assert result.match_score <= 79
        assert any("Location mismatch" in warning for warning in result.warnings)
    assert_explainable(result)


@pytest.mark.parametrize("changes", [
    {"preferred_city": None, "preferred_pincode": None},
    {"preferred_state": None, "preferred_pincode": None},
    {"preferred_state": None, "preferred_city": None},
])
def test_only_supplied_location_preferences_are_compared(changes):
    assert points(evaluate_warehouse_match(requirement(**changes), warehouse()), "location") == 30


@pytest.mark.parametrize("status,expected", [
    (AvailabilityStatus.AVAILABLE, 100), (AvailabilityStatus.PARTIALLY_OCCUPIED, 59),
    (AvailabilityStatus.OCCUPIED, 39), (AvailabilityStatus.UNDER_MAINTENANCE, 39),
    (AvailabilityStatus.INACTIVE, 39), (None, 39),
])
def test_availability_safety(status, expected):
    result = evaluate_warehouse_match(requirement(), warehouse(availability_status=status))
    assert result.match_score == expected
    assert_explainable(result)


@pytest.mark.parametrize("occupancy", [-1, 1, 100, 101, Decimal("NaN")])
def test_contradictory_occupancy_cannot_be_excellent(occupancy):
    result = evaluate_warehouse_match(requirement(), warehouse(occupancy_rate=occupancy))
    assert result.match_score == 59
    assert any("Occupancy rate" in warning for warning in result.warnings)


def test_available_from_does_not_introduce_wall_clock_scoring():
    first = evaluate_warehouse_match(requirement(), warehouse(available_from=datetime(2000, 1, 1)))
    second = evaluate_warehouse_match(requirement(), warehouse(available_from=datetime(2100, 1, 1)))
    assert first == second
    assert any("move-in" in warning for warning in first.warnings)


@pytest.mark.parametrize("kind", list(WarehouseType))
def test_type_comparison_does_not_invent_substitutions(kind):
    result = evaluate_warehouse_match(requirement(), warehouse(warehouse_type=kind))
    assert points(result, "type") == (15 if kind == WarehouseType.COVERED else 0)
    if kind not in (WarehouseType.COVERED, WarehouseType.OTHER):
        assert result.match_score <= 59
    assert_explainable(result)


@pytest.mark.parametrize("score,level", [(0, "POOR"), (39, "POOR"), (40, "PARTIAL"), (59, "PARTIAL"), (60, "GOOD"), (79, "GOOD"), (80, "EXCELLENT"), (100, "EXCELLENT")])
def test_classification_boundaries(score, level):
    assert classify_match(score) == level


@pytest.mark.parametrize("score", [-1, 101])
def test_classification_rejects_invalid_scores(score):
    with pytest.raises(ValueError):
        classify_match(score)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False)() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def saved_requirement(db_session):
    org = Organization(public_id="matching-org", org_code="MATCH", legal_name="Owner",
                       org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE,
                       status=OrganizationStatus.ACTIVE)
    company = Company(organization_owners=org, company_name="Customer", industry="Logistics", company_type="Private")
    lead = Lead(lead_number="MATCH-1", company=company)
    user = User(id=1, full_name="Owner", email="match@example.com", hashed_password="unused", role="user")
    db_session.add_all([lead, user])
    db_session.flush()
    db_session.add(OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role=OrganizationMemberRole.VIEWER,
    ))
    req = requirement(lead_id=lead.id)
    db_session.add(req)
    db_session.commit()
    return req


def test_ranking_ties_limits_query_count_and_workflow_preserved(db_session, saved_requirement):
    stocks = [warehouse(id=i) for i in range(1, 206)]
    stocks[0].built_up_area_sqft = 1
    stocks[1].city = "Mysuru"
    stocks[2].availability_status = AvailabilityStatus.PARTIALLY_OCCUPIED
    db_session.add_all(stocks)
    db_session.flush()
    saved = WarehouseMatch(lead_id=saved_requirement.lead_id, requirement_id=1, warehouse_id=4,
                           match_score=12, match_rank=77, status=WarehouseMatchStatus.REJECTED,
                           matched_by=MatchedBy.MANUAL, notes="Keep review", match_reasons="Manual reasons")
    db_session.add(saved)
    db_session.commit()
    req_id, saved_id = saved_requirement.id, saved.id
    db_session.expunge_all()
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(db_session.bind, "before_cursor_execute", capture)
    try:
        result = WarehouseMatchService().recommend_for_requirement(db_session, req_id, limit=5)
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture)
    assert len(statements) == 2
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert result.candidates_evaluated == 205
    assert [match.warehouse_id for match in result.matches] == [4, 5, 6, 7, 8]
    assert [match.match_rank for match in result.matches] == [1, 2, 3, 4, 5]
    assert result.matches[0].existing_match_id == saved_id
    assert result.matches[0].existing_match_status == WarehouseMatchStatus.REJECTED
    assert result == WarehouseMatchService().recommend_for_requirement(db_session, req_id, limit=5)
    assert not db_session.new and not db_session.dirty and not db_session.deleted
    db_session.expire_all()
    persisted = db_session.get(WarehouseMatch, saved_id)
    assert persisted.match_score == 12 and persisted.match_rank == 77
    assert persisted.notes == "Keep review" and persisted.match_reasons == "Manual reasons"
    assert persisted.matched_by == MatchedBy.MANUAL
    assert len(db_session.scalars(select(WarehouseMatch)).all()) == 1
    assert persisted.requirement.lead.company.company_name == "Customer"
    assert persisted.warehouse.matches[0] is persisted


def test_candidate_selection_all_statuses_and_no_implicit_first_100_cutoff(db_session, saved_requirement):
    for index, status in enumerate([*AvailabilityStatus, None], 1):
        db_session.add(warehouse(id=index, availability_status=status))
    db_session.commit()
    result = WarehouseMatchService().recommend_for_requirement(db_session, 1)
    assert result.candidates_evaluated == 2
    assert [match.warehouse_id for match in result.matches] == [1, 2]
    assert [match.match_score for match in result.matches] == [100, 59]


def test_best_candidate_after_first_batch_replaces_heap_minimum(db_session, saved_requirement):
    db_session.add_all([warehouse(id=index, built_up_area_sqft=1) for index in range(1, 205)])
    db_session.add(warehouse(id=205))
    db_session.commit()
    result = WarehouseMatchService().recommend_for_requirement(db_session, 1, limit=2)
    assert result.candidates_evaluated == 205
    assert [item.warehouse_id for item in result.matches] == [205, 1]
    assert [item.match_score for item in result.matches] == [100, 39]


def test_saved_changes_are_recalculated_without_stale_cache(db_session, saved_requirement):
    stock = warehouse()
    db_session.add(stock)
    db_session.commit()
    service = WarehouseMatchService()
    assert service.recommend_for_requirement(db_session, 1).matches[0].match_score == 100
    stock.built_up_area_sqft = 1
    db_session.commit()
    assert service.recommend_for_requirement(db_session, 1).matches[0].match_score == 39
    stock.availability_status = AvailabilityStatus.INACTIVE
    db_session.commit()
    assert service.recommend_for_requirement(db_session, 1).matches == []


def test_empty_unknown_requirement_and_unsupported_criteria(db_session, saved_requirement):
    saved_requirement.requirement_status = RequirementStatus.DRAFT
    saved_requirement.fire_noc_required = True
    saved_requirement.required_floor_load = 500
    db_session.commit()
    service = WarehouseMatchService()
    result = service.recommend_for_requirement(db_session, 1)
    assert result.matches == [] and result.candidates_evaluated == 0
    assert any("not ACTIVE" in warning for warning in result.warnings)
    assert any("fire_noc_required" in warning and "required_floor_load" in warning for warning in result.warnings)
    assert service.recommend_for_requirement(db_session, 9999) is None


@pytest.mark.parametrize("limit", [0, -1, 101])
def test_service_validates_limit(db_session, limit):
    with pytest.raises(ValueError, match="limit"):
        WarehouseMatchService().recommend_for_requirement(db_session, 1, limit=limit)


@pytest.mark.parametrize("pending", ["new", "dirty", "deleted"])
def test_read_only_service_rejects_pending_changes(db_session, saved_requirement, pending):
    if pending == "new":
        db_session.add(warehouse())
    elif pending == "dirty":
        saved_requirement.title = "Unsaved"
    else:
        db_session.delete(saved_requirement)
    with pytest.raises(ValueError, match="pending changes"):
        WarehouseMatchService().recommend_for_requirement(db_session, 1)


@pytest.fixture()
def client(db_session):
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


def headers(email="match@example.com"):
    return {"Authorization": "Bearer " + create_access_token({"sub": email})}


URL = "/warehouse-matches/requirements/1/recommendations"


def test_api_auth_and_schema_and_repeatability(client, db_session, saved_requirement):
    db_session.add_all([
        warehouse(id=2, organization_id=saved_requirement.lead.company.organization_id),
        warehouse(id=1, organization_id=saved_requirement.lead.company.organization_id),
    ])
    db_session.commit()
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"Authorization": "Bearer invalid"}).status_code == 401
    assert client.get(URL, headers=headers("missing@example.com")).status_code == 401
    response = client.get(URL, headers=headers())
    assert response.status_code == 200
    data = response.json()
    assert data["requirement_id"] == 1 and data["lead_id"] == saved_requirement.lead_id
    assert data["scoring_version"] == "warehouse-rules-v1"
    assert [match["warehouse_id"] for match in data["matches"]] == [1, 2]
    assert data["matches"][0]["match_level"] == "EXCELLENT"
    assert len(data["matches"][0]["reasons"]) == 4
    assert "owner_id" not in data["matches"][0]
    assert data == client.get(URL, headers=headers()).json()
    assert client.post("/warehouse-matches/", headers=headers(), json={
        "lead_id": 1, "requirement_id": 1, "warehouse_id": 1,
        "match_score": 100, "status": "SHORTLISTED", "matched_by": "MANUAL",
    }).status_code == 403
    assert len(client.get(URL + "?limit=1", headers=headers()).json()["matches"]) == 1
    assert client.get("/warehouse-matches/requirements/9999/recommendations", headers=headers()).json() == {"detail": "Requirement not found"}
    assert client.get("/warehouse-matches/requirements/9999/recommendations", headers=headers()).status_code == 404
    for limit in (0, -1, 101, "bad"):
        assert client.get(URL + f"?limit={limit}", headers=headers()).status_code == 422
    user = db_session.get(User, 1)
    user.is_active = False
    db_session.commit()
    assert client.get(URL, headers=headers()).status_code == 401


def test_existing_saved_match_api_still_exposes_manual_workflow(client, db_session, saved_requirement):
    db_session.add(warehouse(organization_id=saved_requirement.lead.company.organization_id))
    db_session.flush()
    saved = WarehouseMatch(lead_id=1, requirement_id=1, warehouse_id=1, match_score=55,
                           status=WarehouseMatchStatus.SHORTLISTED, matched_by=MatchedBy.MANUAL)
    db_session.add(saved)
    db_session.commit()
    match_id = saved.id
    before = client.get(f"/warehouse-matches/{match_id}", headers=headers()).json()
    assert client.get(URL, headers=headers()).json()["matches"][0]["match_score"] == 100
    after = client.get(f"/warehouse-matches/{match_id}", headers=headers()).json()
    assert before == after
    assert after["match_score"] == 55 and after["status"] == "SHORTLISTED"
    assert client.get("/warehouse-matches/?requirement_id=1", headers=headers()).json() == [after]