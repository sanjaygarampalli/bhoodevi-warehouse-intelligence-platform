"""Deal workflow through real JWT routes and a foreign-key-enforced database."""
from datetime import datetime, timezone

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
    Deal, DealPipelineStage, DealStageHistory, Lead, OrganizationMemberRole,
    OrganizationMembership, Requirement, User, WarehouseMatch,
)
from app.schemas.deal import DealCreate, DealTransition, DealUpdate
from app.schemas.deal_pipeline_stage import DealPipelineStageUpdate
from app.services.deal import DealService
from app.services.deal_pipeline_stage import DealPipelineStageService
from app.services.deal_workflow import DealConflict, DealNotFound


@pytest.fixture()
def context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    db.add_all([
        User(id=1, full_name="Admin", email="deal-admin@example.com", role="admin", hashed_password="unused"),
        User(id=2, full_name="Reader", email="deal-reader@example.com", role="user", hashed_password="unused"),
        User(id=3, full_name="Inactive", email="deal-inactive@example.com", role="admin", hashed_password="unused", is_active=False),
    ])
    db.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = "Bearer " + create_access_token({"sub": "deal-admin@example.com"})
            yield client, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def post(client, path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def flow(context):
    client, db = context
    industry = post(client, "/industries/", {"code": "DEAL", "name": "Distribution"})
    org = post(client, "/organizations/", {
        "org_code": "DEAL", "legal_name": "Warehouse Leasing", "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE", "industry_id": industry["id"],
    })
    company = post(client, "/companies/", {
        "organization_id": org["id"], "company_name": "Prospect", "industry": industry["name"], "company_type": "Private",
    })
    lead = post(client, "/leads/", {"lead_number": "DEAL-1", "company_id": company["id"]})
    db.add(OrganizationMembership(
        user_id=2,
        organization_id=org["id"],
        role=OrganizationMemberRole.VIEWER,
    ))
    db.commit()
    requirement = post(client, f"/leads/{lead['id']}/requirements/", {
        "lead_id": lead["id"], "title": "Distribution space", "minimum_area": 1000,
        "preferred_city": "Bengaluru", "requirement_status": "ACTIVE",
    })
    warehouse = post(client, "/warehouses/", {
        "warehouse_name": "Distribution Park", "owner_id": 1, "city": "Bengaluru", "state": "Karnataka",
        "total_area_sqft": 1000, "warehouse_type": "COVERED", "availability_status": "AVAILABLE",
    })
    post(client, f"/warehouse-matches/requirements/{requirement['id']}/generate", {})
    match = client.get(f"/warehouse-matches/?requirement_id={requirement['id']}").json()[0]
    stages = {}
    for order, key in enumerate(("QUALIFICATION", "REQUIREMENT_CONFIRMED", "WAREHOUSE_SHORTLISTED", "SITE_VISIT",
                                 "COMMERCIAL_DISCUSSION", "NEGOTIATION", "WON", "LOST"), 1):
        stages[key] = post(client, "/deal-pipeline-stages/", {
            "organization_id": org["id"], "stage_key": key, "stage_name": key.replace("_", " ").title(),
            "stage_order": order * 10, "is_terminal": key in ("WON", "LOST"),
            "is_won": key == "WON", "is_lost": key == "LOST",
        })
    return {"client": client, "db": db, "org": org, "company": company, "lead": lead,
            "requirement": requirement, "warehouse": warehouse, "match": match, "stages": stages}


def payload(flow, **changes):
    return {"deal_name": "Bengaluru distribution lease", "lead_id": flow["lead"]["id"],
            "requirement_id": flow["requirement"]["id"], "stage_id": flow["stages"]["QUALIFICATION"]["id"], **changes}


def create(flow, **changes):
    return post(flow["client"], "/deals/", payload(flow, **changes))


def transition(flow, deal, key):
    return post(flow["client"], f"/deals/{deal['id']}/transition", {
        "to_stage_id": flow["stages"][key]["id"], "change_reason": f"Approved {key}",
    })


def test_complete_leasing_flow_and_immutable_history(flow):
    client = flow["client"]
    deal = create(flow, expected_revenue="1200000.00", expected_close_date="2026-12-01")
    path = f"/deals/{deal['id']}"
    original = client.get(path + "/history").json()
    assert len(original) == 1 and original[0]["from_stage_id"] is None
    assert original[0]["changed_by_user_id"] == 1
    for key in ("REQUIREMENT_CONFIRMED", "WAREHOUSE_SHORTLISTED", "SITE_VISIT", "COMMERCIAL_DISCUSSION", "NEGOTIATION"):
        transition(flow, deal, key)
    selected = client.put(path, json={"selected_warehouse_match_id": flow["match"]["id"], "notes": "Preferred site"})
    assert selected.status_code == 200, selected.text
    assert selected.json()["selected_warehouse_match_id"] == flow["match"]["id"]
    assert client.get(f"/warehouse-matches/{flow['match']['id']}").json() == flow["match"]
    stage_path = f"/deal-pipeline-stages/{flow['stages']['QUALIFICATION']['id']}"
    assert client.put(stage_path, json={"stage_name": "Initial assessment"}).status_code == 200
    assert client.get(path + "/history").json()[-1] == original[0]
    won = transition(flow, deal, "WON")
    assert won["deal_status"] == "WON" and won["closed_at"] and won["closed_reason"] == "Approved WON"
    history = client.get(path + "/history").json()
    assert len(history) == 7
    assert [h["id"] for h in history] == sorted([h["id"] for h in history], reverse=True)
    assert all(h["from_stage_id"] == history[i + 1]["to_stage_id"] for i, h in enumerate(history[:-1]))
    assert client.get(path + "/history?skip=1&limit=2").json() == history[1:3]
    assert client.post(path + "/transition", json={"to_stage_id": deal["stage_id"]}).status_code == 409
    assert client.put(path, json={"notes": "reopen"}).status_code == 409
    assert transition(flow, deal, "WON") == won
    assert client.get(path + "/history").json() == history
    assert client.get(path).json() == won


@pytest.mark.parametrize("field,value,status", [
    ("lead_id", 999, 404), ("requirement_id", 999, 404), ("selected_warehouse_match_id", 999, 404),
    ("stage_id", 999, 404), ("deal_name", "  ", 422), ("lead_id", None, 422),
    ("expected_revenue", -1, 422), ("expected_revenue", "1.001", 422), ("currency", "rupee", 422),
])
def test_create_invalid_fields(flow, field, value, status):
    response = flow["client"].post("/deals/", json=payload(flow, **{field: value}))
    assert response.status_code == status, response.text
    assert flow["db"].scalar(select(Deal.id)) is None
    assert flow["db"].scalar(select(DealStageHistory.id)) is None


@pytest.mark.parametrize("key", ["WON", "LOST"])
def test_terminal_protection(flow, key):
    client = flow["client"]
    assert client.post("/deals/", json=payload(flow, stage_id=flow["stages"][key]["id"])).status_code == 409
    deal = create(flow)
    transition(flow, deal, key)
    path = f"/deals/{deal['id']}"
    before = client.get(path + "/history").json()
    assert client.post(path + "/transition", json={"to_stage_id": deal["stage_id"]}).status_code == 409
    assert client.put(path, json={"selected_warehouse_match_id": flow["match"]["id"]}).status_code == 409
    assert client.get(path + "/history").json() == before
    assert create(flow)["id"] != deal["id"]


def test_noop_invalid_stage_and_explicit_updates(flow):
    client = flow["client"]
    deal = create(flow)
    path = f"/deals/{deal['id']}"
    assert client.post(path + "/transition", json={"to_stage_id": deal["stage_id"]}).json() == deal
    assert client.post(path + "/transition", json={"to_stage_id": 999}).status_code == 404
    assert len(client.get(path + "/history").json()) == 1
    for field in ("stage_id", "lead_id", "requirement_id", "deal_status", "closed_at"):
        assert client.put(path, json={field: 1}).status_code == 422
    response = client.put(path, json={"deal_name": "Updated", "notes": "Call scheduled"})
    assert response.status_code == 200 and response.json()["deal_name"] == "Updated"
    assert len(client.get(path + "/history").json()) == 1


def test_transition_rejects_stage_from_another_organization(flow):
    client = flow["client"]
    deal = create(flow)
    other_org = post(client, "/organizations/", {
        "org_code": "OTHERORG", "legal_name": "Other organization", "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE",
    })
    other_stage = post(client, "/deal-pipeline-stages/", {
        "organization_id": other_org["id"], "stage_key": "OTHER", "stage_name": "Other", "stage_order": 0,
    })

    response = client.post(
        f"/deals/{deal['id']}/transition",
        json={"to_stage_id": other_stage["id"]},
    )

    assert response.status_code == 409
    assert client.get(f"/deals/{deal['id']}").json()["stage_id"] == deal["stage_id"]
    assert len(client.get(f"/deals/{deal['id']}/history").json()) == 1


@pytest.mark.parametrize("boundary", ["requirement_lead", "match_lead", "match_requirement"])
def test_cross_opportunity_boundaries_in_service_and_api(flow, boundary):
    db, client = flow["db"], flow["client"]
    other = Lead(lead_number="OTHER", company_id=flow["company"]["id"])
    db.add(other)
    db.flush()
    req = Requirement(lead_id=other.id, title="Other demand")
    db.add(req)
    db.commit()
    data = payload(flow, selected_warehouse_match_id=flow["match"]["id"])
    if boundary == "requirement_lead":
        data["requirement_id"] = req.id
    else:
        match = db.get(WarehouseMatch, flow["match"]["id"])
        if boundary == "match_lead":
            match.lead_id = other.id
        else:
            match.requirement_id = req.id
        db.commit()
    with pytest.raises(DealConflict):
        DealService().create_deal(db, DealCreate(**data), 1)
    assert client.post("/deals/", json=data).status_code == 409
    assert db.scalar(select(Deal.id)) is None


@pytest.mark.parametrize("status", ["STALE", "REJECTED", "CONVERTED"])
def test_unselectable_match(flow, status):
    db = flow["db"]
    db.get(WarehouseMatch, flow["match"]["id"]).status = status
    db.commit()
    response = flow["client"].post("/deals/", json=payload(flow, selected_warehouse_match_id=flow["match"]["id"]))
    assert response.status_code == 409


def test_match_selection_update_validation_and_clear(flow):
    client, db = flow["client"], flow["db"]
    deal = create(flow)
    path = f"/deals/{deal['id']}"
    assert client.put(path, json={"selected_warehouse_match_id": 999}).status_code == 404
    match = db.get(WarehouseMatch, flow["match"]["id"])
    match.requirement_id = None
    db.commit()
    assert client.put(path, json={"selected_warehouse_match_id": match.id}).status_code == 200
    assert client.put(path, json={"selected_warehouse_match_id": None}).json()["selected_warehouse_match_id"] is None
    assert client.put(f"/warehouses/{flow['warehouse']['id']}", json={"availability_status": "INACTIVE"}).status_code == 200
    assert client.put(path, json={"selected_warehouse_match_id": match.id}).status_code == 409


def test_duplicate_active_deal_and_listing_filters(flow):
    client = flow["client"]
    first = create(flow)
    assert client.post("/deals/", json=payload(flow)).status_code == 409
    assert len(client.get("/deals/").json()) == 1
    transition(flow, first, "LOST")
    second = create(flow)
    assert [d["id"] for d in client.get("/deals/").json()] == [second["id"], first["id"]]
    for query in ("is_active=true", f"stage_id={second['stage_id']}"):
        assert [d["id"] for d in client.get("/deals/?" + query).json()] == [second["id"]]
    assert client.get("/deals/?is_active=false").json()[0]["id"] == first["id"]
    assert client.get("/deals/?skip=1&limit=1").json()[0]["id"] == first["id"]
    assert len(client.get(f"/deals/?lead_id={first['lead_id']}&organization_id={first['organization_id']}").json()) == 2
    assert client.get("/deals/?lead_id=999").json() == []


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_history_orm_mutation_rejected(flow, operation):
    create(flow)
    db = flow["db"]
    history = db.scalar(select(DealStageHistory))
    if operation == "update":
        history.change_reason = "rewritten"
    else:
        db.delete(history)
    with pytest.raises(ValueError, match="immutable"):
        db.commit()
    db.rollback()
    assert db.scalar(select(DealStageHistory)).change_reason == "Deal created"


def test_history_timestamp_tie_order(flow, monkeypatch):
    import app.services.deal as module

    class Clock:
        @staticmethod
        def now(tz):
            return datetime(2026, 9, 9, tzinfo=timezone.utc)

    monkeypatch.setattr(module, "datetime", Clock)
    deal = create(flow)
    transition(flow, deal, "SITE_VISIT")
    transition(flow, deal, "NEGOTIATION")
    history = flow["client"].get(f"/deals/{deal['id']}/history").json()
    assert len({h["changed_at"] for h in history}) == 1
    assert [h["id"] for h in history] == sorted([h["id"] for h in history], reverse=True)


@pytest.mark.parametrize("creating", [True, False])
def test_failed_history_insert_rolls_back_entire_workflow(flow, creating):
    db = flow["db"]
    deal = None if creating else create(flow)

    def fail(mapper, connection, target):
        raise IntegrityError("injected history failure", {}, Exception("failure"))

    event.listen(DealStageHistory, "before_insert", fail)
    try:
        with pytest.raises(DealConflict):
            if creating:
                DealService().create_deal(db, DealCreate(**payload(flow)), 1)
            else:
                DealService().transition_deal(db, deal["id"], DealTransition(to_stage_id=flow["stages"]["WON"]["id"]), 1)
    finally:
        event.remove(DealStageHistory, "before_insert", fail)
    if creating:
        assert db.scalar(select(Deal.id)) is None
        assert db.scalar(select(DealStageHistory.id)) is None
        create(flow)
    else:
        assert db.get(Deal, deal["id"]).deal_status == "OPEN"
        assert db.get(Deal, deal["id"]).stage_id == deal["stage_id"]
        assert len(DealService().get_history(db, deal["id"])) == 1
        transition(flow, deal, "WON")


@pytest.mark.parametrize("entity", ["lead", "requirement", "match", "warehouse", "company"])
def test_referenced_source_deletion_is_clean_conflict(flow, entity):
    create(flow, selected_warehouse_match_id=flow["match"]["id"])
    paths = {"lead": f"/leads/{flow['lead']['id']}",
             "requirement": f"/leads/{flow['lead']['id']}/requirements/{flow['requirement']['id']}",
             "match": f"/warehouse-matches/{flow['match']['id']}",
             "warehouse": f"/warehouses/{flow['warehouse']['id']}",
             "company": f"/companies/{flow['company']['id']}"}
    response = flow["client"].delete(paths[entity])
    assert response.status_code == 409, response.text
    assert len(flow["client"].get("/deals/").json()) == 1


def test_source_reassignment_guards(flow):
    from app.schemas.requirement import RequirementUpdate
    from app.services.requirement import RequirementService

    create(flow, selected_warehouse_match_id=flow["match"]["id"])
    db, client = flow["db"], flow["client"]
    with pytest.raises(DealConflict):
        RequirementService().update_requirement(db, flow["requirement"]["id"], RequirementUpdate(lead_id=999))
    for path, changes in (
        (f"/leads/{flow['lead']['id']}", {"company_id": 999}),
        (f"/warehouse-matches/{flow['match']['id']}", {"lead_id": 999}),
        (f"/warehouse-matches/{flow['match']['id']}", {"warehouse_id": 999}),
        (f"/warehouse-matches/{flow['match']['id']}", {"requirement_id": None}),
    ):
        response = client.put(path, json=changes)
        assert response.status_code == 409, response.text
    # Existing CompanyUpdate does not expose ownership changes (unknown fields are ignored).
    response = client.put(f"/companies/{flow['company']['id']}", json={"organization_id": 999})
    assert response.status_code == 200
    assert response.json()["organization_id"] == flow["org"]["id"]


@pytest.mark.parametrize("table", [Lead, Requirement, WarehouseMatch, DealPipelineStage, Deal])
def test_database_foreign_keys_protect_referenced_records(flow, table):
    create(flow, selected_warehouse_match_id=flow["match"]["id"])
    db = flow["db"]
    with pytest.raises(IntegrityError):
        db.execute(delete(table))
        db.commit()
    db.rollback()
    assert db.scalar(select(DealStageHistory.id)) is not None


def test_list_uses_one_query_not_n_plus_one(flow):
    from app.schemas.deal import DealResponse

    deal = create(flow)
    transition(flow, deal, "LOST")
    create(flow)
    db = flow["db"]
    db.expire_all()
    statements = []

    def capture(conn, cursor, statement, params, context, many):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        results = DealService().list_deals(db)
        assert len([DealResponse.model_validate(d) for d in results]) == 2
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)
    assert len(statements) == 1


def test_stage_crud_ordering_and_deletion_protection(flow):
    client = flow["client"]
    stages = client.get(f"/deal-pipeline-stages/?organization_id={flow['org']['id']}").json()
    assert [s["stage_order"] for s in stages] == list(range(10, 81, 10))
    assert client.get("/deal-pipeline-stages/?skip=2&limit=2").json() == stages[2:4]
    stage = stages[0]
    path = f"/deal-pipeline-stages/{stage['id']}"
    assert client.get(path).json() == stage
    deal = create(flow)
    assert client.delete(path).status_code == 409
    transition(flow, deal, "SITE_VISIT")
    assert client.delete(path).status_code == 409  # history-only reference
    for changes in ({"stage_key": "RENAMED"}, {"is_terminal": True, "is_won": True}):
        assert client.put(path, json=changes).status_code == 409
    assert client.put(path, json={"description": "Updated", "stage_order": 5, "is_active": False}).status_code == 200
    assert len(client.get("/deal-pipeline-stages/?is_active=true").json()) == 7
    assert client.delete(f"/deal-pipeline-stages/{stages[-1]['id']}").status_code == 200
    assert client.get(f"/deal-pipeline-stages/{stages[-1]['id']}").status_code == 404


@pytest.mark.parametrize("changes,status", [
    ({"stage_key": "QUALIFICATION"}, 409), ({"stage_order": 10}, 409),
    ({"stage_key": "lowercase"}, 422), ({"stage_name": " "}, 422),
    ({"stage_order": -1}, 422), ({"organization_id": 999}, 404),
    ({"is_terminal": True}, 409), ({"is_won": True}, 409),
    ({"is_terminal": True, "is_won": True, "is_lost": True}, 409),
])
def test_stage_validation(flow, changes, status):
    response = flow["client"].post("/deal-pipeline-stages/", json={
        "organization_id": flow["org"]["id"], "stage_key": "EXTRA", "stage_name": "Extra", "stage_order": 90, **changes,
    })
    assert response.status_code == status, response.text


def test_stage_update_validation_and_same_name_allowed(flow):
    client = flow["client"]
    path = f"/deal-pipeline-stages/{flow['stages']['SITE_VISIT']['id']}"
    for changes, status in (({"stage_name": None}, 422), ({"is_active": None}, 422),
                            ({"stage_order": 10}, 409), ({"stage_key": "QUALIFICATION"}, 409),
                            ({"is_won": True}, 409)):
        assert client.put(path, json=changes).status_code == status
    assert client.put(path, json={"stage_name": "Qualification"}).status_code == 200
    assert client.put(path, json={"is_terminal": True, "is_lost": True}).status_code == 200


def test_inactive_and_other_organization_stage(flow):
    client = flow["client"]
    stage = flow["stages"]["SITE_VISIT"]
    assert client.put(f"/deal-pipeline-stages/{stage['id']}", json={"is_active": False}).status_code == 200
    assert client.post("/deals/", json=payload(flow, stage_id=stage["id"])).status_code == 409
    deal = create(flow)
    assert client.post(f"/deals/{deal['id']}/transition", json={"to_stage_id": stage["id"]}).status_code == 409
    org = post(client, "/organizations/", {"org_code": "OTHER", "legal_name": "Other", "org_type": "PVT_LTD",
                                          "subscription_tier": "FREE", "status": "ACTIVE"})
    other = post(client, "/deal-pipeline-stages/", {"organization_id": org["id"], "stage_key": "QUALIFICATION",
                                                   "stage_name": "Qualification", "stage_order": 10})
    assert client.post(f"/deals/{deal['id']}/transition", json={"to_stage_id": other["id"]}).status_code == 409
    assert client.post("/deals/", json=payload(flow, stage_id=other["id"])).status_code == 409


@pytest.mark.parametrize("path", ["/deals/", "/deal-pipeline-stages/", "/deals/999/history"])
@pytest.mark.parametrize("query", ["limit=0", "limit=101", "skip=-1"])
def test_pagination_validation(context, path, query):
    assert context[0].get(path + "?" + query).status_code == 422


@pytest.mark.parametrize("method,path,data", [
    ("get", "/deals/999", None), ("get", "/deals/999/history", None),
    ("put", "/deals/999", {"notes": "x"}), ("post", "/deals/999/transition", {"to_stage_id": 1}),
    ("get", "/deal-pipeline-stages/999", None), ("put", "/deal-pipeline-stages/999", {"stage_name": "x"}),
    ("delete", "/deal-pipeline-stages/999", None),
])
def test_missing_resources(context, method, path, data):
    assert context[0].request(method, path, json=data).status_code == 404


@pytest.mark.parametrize("identity,read_status,write_status", [
    (None, 401, 401), ("reader", 200, 403), ("inactive", 401, 401),
])
def test_real_jwt_authentication_and_roles(flow, identity, read_status, write_status):
    client = flow["client"]
    deal = create(flow)
    if identity is None:
        client.headers.pop("Authorization")
    else:
        client.headers["Authorization"] = "Bearer " + create_access_token({"sub": f"deal-{identity}@example.com"})
    for path in ("/deals/", f"/deals/{deal['id']}", f"/deals/{deal['id']}/history", "/deal-pipeline-stages/",
                 f"/deal-pipeline-stages/{deal['stage_id']}"):
        if path == "/deals/" and identity == "reader":
            path += f"?organization_id={flow['org']['id']}"
        assert client.get(path).status_code == read_status
    for method, path, data in (
        ("post", "/deals/", payload(flow)), ("put", f"/deals/{deal['id']}", {"notes": "x"}),
        ("post", f"/deals/{deal['id']}/transition", {"to_stage_id": deal["stage_id"]}),
        ("post", "/deal-pipeline-stages/", {"organization_id": flow["org"]["id"], "stage_name": "x", "stage_key": "X", "stage_order": 99}),
        ("put", f"/deal-pipeline-stages/{deal['stage_id']}", {"stage_name": "x"}),
        ("delete", f"/deal-pipeline-stages/{deal['stage_id']}", None),
    ):
        assert client.request(method, path, json=data).status_code == write_status


def test_service_checks_actor_and_pagination(flow):
    db = flow["db"]
    with pytest.raises(DealNotFound, match="User"):
        DealService().create_deal(db, DealCreate(**payload(flow)), 999)
    with pytest.raises(DealConflict, match="active"):
        DealService().create_deal(db, DealCreate(**payload(flow)), 3)
    with pytest.raises(DealConflict, match="Pagination"):
        DealService().list_deals(db, limit=101)
    with pytest.raises(DealConflict, match="Pagination"):
        DealPipelineStageService().list_stages(db, skip=-1)
    stage = flow["stages"]["QUALIFICATION"]
    with pytest.raises(DealConflict, match="outcome"):
        DealPipelineStageService().update_stage(db, stage["id"], DealPipelineStageUpdate(is_won=True))
    deal = DealService().create_deal(db, DealCreate(**payload(flow)))
    assert DealService().get_history(db, deal.id)[0].changed_by_user_id is None


def test_stage_only_organization_deletion_conflict_recovers_session(context):
    client, db = context
    org = post(client, "/organizations/", {
        "org_code": "STAGES", "legal_name": "Stage owner", "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE",
    })
    stage = post(client, "/deal-pipeline-stages/", {
        "organization_id": org["id"], "stage_key": "NEW", "stage_name": "New", "stage_order": 10,
    })
    assert client.delete(f"/organizations/{org['id']}").status_code == 409
    assert db.get(DealPipelineStage, stage["id"]) is not None
    assert client.delete(f"/deal-pipeline-stages/{stage['id']}").status_code == 200
    assert client.delete(f"/organizations/{org['id']}").status_code == 200


def test_workflow_does_not_commit_unrelated_pending_changes(flow):
    db = flow["db"]
    lead = db.get(Lead, flow["lead"]["id"])
    lead.lead_number = "UNCOMMITTED"
    with pytest.raises(DealConflict, match="pending changes"):
        DealService().create_deal(db, DealCreate(**payload(flow)), 1)
    assert lead in db.dirty
    db.rollback()
    assert db.scalar(select(Deal.id)) is None
    assert lead.lead_number == "DEAL-1"
    create(flow)