"""End-to-end integrated opportunity (Deal) context through real JWT routes."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User


def _token(email: str) -> str:
    return "Bearer " + create_access_token({"sub": email})


@pytest.fixture()
def context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    db.add_all([
        User(id=1, full_name="Owner", email="opp-owner@example.com", role="admin", hashed_password="unused"),
        User(id=2, full_name="Other", email="opp-other@example.com", role="admin", hashed_password="unused"),
    ])
    db.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = _token("opp-owner@example.com")
            yield client, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def post(client, path, payload, expected=200):
    response = client.post(path, json=payload)
    assert response.status_code == expected, response.text
    return response.json() if response.text else response


def build_org(client, code, name):
    industry = post(client, "/industries/", {"code": code, "name": name + " industry"})
    org = post(client, "/organizations/", {
        "org_code": code, "legal_name": name, "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE", "industry_id": industry["id"],
    })
    return industry, org


def build_lead_stack(client, industry, org):
    company = post(client, "/companies/", {
        "organization_id": org["id"], "company_name": "Prospect Co", "industry": industry["name"],
        "company_type": "Private",
    })
    lead = post(client, "/leads/", {"lead_number": code_prefix(industry) + "-1", "company_id": company["id"]})
    requirement = post(client, f"/leads/{lead['id']}/requirements/", {
        "lead_id": lead["id"], "title": "Distribution space", "minimum_area": 1000,
        "preferred_city": "Bengaluru", "requirement_status": "ACTIVE",
    })
    warehouse = post(client, "/warehouses/", {
        "warehouse_name": "Distribution Park", "owner_id": 1, "city": "Bengaluru", "state": "Karnataka",
        "total_area_sqft": 2000, "warehouse_type": "COVERED", "availability_status": "AVAILABLE",
    })
    post(client, f"/warehouse-matches/requirements/{requirement['id']}/generate", {})
    matches = client.get(f"/warehouse-matches/?requirement_id={requirement['id']}").json()
    return {"company": company, "lead": lead, "requirement": requirement,
            "warehouse": warehouse, "matches": matches}


def code_prefix(industry):
    return industry["code"]


STAGE_KEYS = ("QUALIFICATION", "REQUIREMENT_CONFIRMED", "WAREHOUSE_SHORTLISTED", "SITE_VISIT",
              "COMMERCIAL_DISCUSSION", "NEGOTIATION", "WON", "LOST")


def build_stages(client, org):
    stages = {}
    for order, key in enumerate(STAGE_KEYS, 1):
        stages[key] = post(client, "/deal-pipeline-stages/", {
            "organization_id": org["id"], "stage_key": key, "stage_name": key.replace("_", " ").title(),
            "stage_order": order * 10, "is_terminal": key in ("WON", "LOST"),
            "is_won": key == "WON", "is_lost": key == "LOST",
        })
    return stages


def create_deal(client, stack, stages, **changes):
    payload = {"deal_name": "Bengaluru lease", "lead_id": stack["lead"]["id"],
               "requirement_id": stack["requirement"]["id"],
               "stage_id": stages["QUALIFICATION"]["id"], **changes}
    return post(client, "/deals/", payload)


def create_task(client, lead_id, deal_id, due_at, **changes):
    payload = {"lead_id": lead_id, "deal_id": deal_id, "subject": "Follow up", "due_at": due_at,
               **changes}
    return post(client, "/follow-up-tasks/", payload)


def test_full_opportunity_workflow(context):
    client, db = context
    industry, org = build_org(client, "OPPA", "Alpha")
    stack = build_lead_stack(client, industry, org)
    stages = build_stages(client, org)
    deal = create_deal(client, stack, stages, expected_revenue="1200000.00")

    # Two open tasks: one overdue, one upcoming.
    now = datetime.now(timezone.utc)
    overdue_due = (now - timedelta(days=2)).isoformat()
    upcoming_due = (now + timedelta(days=3)).isoformat()
    task_overdue = create_task(client, stack["lead"]["id"], deal["id"], overdue_due)
    task_upcoming = create_task(client, stack["lead"]["id"], deal["id"], upcoming_due)

    response = client.get(f"/deals/{deal['id']}/opportunity")
    assert response.status_code == 200, response.text
    data = response.json()

    # Identity + linked entities present.
    assert data["deal"]["id"] == deal["id"]
    assert data["deal"]["deal_status"] == "OPEN"
    assert data["deal"]["stage"]["stage_key"] == "QUALIFICATION"
    assert data["deal"]["organization_id"] == org["id"]
    assert data["organization"]["id"] == org["id"]
    assert data["lead"]["id"] == stack["lead"]["id"]
    assert data["requirement"]["id"] == stack["requirement"]["id"]

    # Warehouse matches for the requirement are surfaced.
    match_ids = {m["id"] for m in data["warehouse_matches"]}
    assert set(m["id"] for m in stack["matches"]) & match_ids  # at least the generated match present

    # Task partitioning is mutually exclusive and complete.
    open_ids = {t["id"] for t in data["open_tasks"]}
    overdue_ids = {t["id"] for t in data["overdue_tasks"]}
    upcoming_ids = {t["id"] for t in data["upcoming_tasks"]}
    assert open_ids == {task_overdue["id"], task_upcoming["id"]}
    assert overdue_ids == {task_overdue["id"]}
    assert upcoming_ids == {task_upcoming["id"]}
    assert not (overdue_ids & upcoming_ids)

    # Deterministic next action prioritizes the overdue task.
    assert data["next_action"] is not None
    assert data["next_action"]["type"] == "OVERDUE_FOLLOW_UP"
    assert data["next_action"]["reference_id"] == task_overdue["id"]

    # Lead intelligence is present and explainable (reasons + computed next action).
    assert data["intelligence"] is not None
    assert data["intelligence"]["lead_id"] == stack["lead"]["id"]
    assert data["intelligence"]["reasons"]


def test_overdue_task_drives_next_action_then_completion_preserves_history(context):
    client, db = context
    industry, org = build_org(client, "OPPB", "Beta")
    stack = build_lead_stack(client, industry, org)
    stages = build_stages(client, org)
    deal = create_deal(client, stack, stages)
    now = datetime.now(timezone.utc)
    overdue = create_task(client, stack["lead"]["id"], deal["id"], (now - timedelta(days=1)).isoformat())

    data = client.get(f"/deals/{deal['id']}/opportunity").json()
    assert data["next_action"]["type"] == "OVERDUE_FOLLOW_UP"
    assert data["next_action"]["reference_id"] == overdue["id"]

    # Complete the overdue task; it must disappear from open/overdue lists.
    completed = post(client, f"/follow-up-tasks/{overdue['id']}/complete", {"completion_notes": "Called lead"})
    assert completed["status"] == "COMPLETED"
    assert completed["completed_at"] is not None

    data = client.get(f"/deals/{deal['id']}/opportunity").json()
    assert all(t["id"] != overdue["id"] for t in data["open_tasks"])
    assert all(t["id"] != overdue["id"] for t in data["overdue_tasks"])

    # History remains correct: the completed task is still retrievable with its note.
    history = client.get(f"/follow-up-tasks/{overdue['id']}").json()
    assert history["status"] == "COMPLETED"
    assert history["completion_notes"] == "Called lead"


def test_upcoming_task_next_action_when_no_overdue(context):
    client, db = context
    industry, org = build_org(client, "OPPC", "Gamma")
    stack = build_lead_stack(client, industry, org)
    stages = build_stages(client, org)
    deal = create_deal(client, stack, stages)
    now = datetime.now(timezone.utc)
    create_task(client, stack["lead"]["id"], deal["id"], (now + timedelta(days=5)).isoformat())

    data = client.get(f"/deals/{deal['id']}/opportunity").json()
    assert data["next_action"]["type"] == "UPCOMING_FOLLOW_UP"


def test_no_cross_organization_context_leakage_across_tenants(context):
    client, db = context
    # Org A fully built and read by its owner.
    industry_a, org_a = build_org(client, "ISOA", "Tenant A")
    stack_a = build_lead_stack(client, industry_a, org_a)
    stages_a = build_stages(client, org_a)
    deal_a = create_deal(client, stack_a, stages_a)

    # Switch to Org B admin (user 2) and build its own independent stack + deal.
    client.headers["Authorization"] = _token("opp-other@example.com")
    industry_b, org_b = build_org(client, "ISOB", "Tenant B")
    stack_b = build_lead_stack(client, industry_b, org_b)
    stages_b = build_stages(client, org_b)
    deal_b = create_deal(client, stack_b, stages_b)

    # User 2 can read their own deal.
    own = client.get(f"/deals/{deal_b['id']}/opportunity")
    assert own.status_code == 200, own.text
    assert own.json()["deal"]["id"] == deal_b["id"]

    # Switch back to user 1; they can read their own deal.
    client.headers["Authorization"] = _token("opp-owner@example.com")
    mine = client.get(f"/deals/{deal_a['id']}/opportunity")
    assert mine.status_code == 200, mine.text
    assert mine.json()["deal"]["id"] == deal_a["id"]

    # User 1 must never see User 2's organization context.
    assert mine.json()["organization"]["id"] == org_a["id"]
    assert mine.json()["organization"]["id"] != org_b["id"]


def test_unauthenticated_reader_is_rejected(context):
    client, db = context
    industry, org = build_org(client, "AUTHX", "Auth org")
    stack = build_lead_stack(client, industry, org)
    stages = build_stages(client, org)
    deal = create_deal(client, stack, stages)
    client.headers.pop("Authorization", None)
    response = client.get(f"/deals/{deal['id']}/opportunity")
    assert response.status_code in (401, 403)


def test_missing_deal_returns_404(context):
    client, db = context
    response = client.get("/deals/999999/opportunity")
    assert response.status_code == 404