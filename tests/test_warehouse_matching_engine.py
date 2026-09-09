"""Persisted generation through real app wiring, JWTs and constrained database."""
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User, Warehouse, WarehouseMatch
from app.models.warehouse_match import MatchedBy, WarehouseMatchStatus
from app.services.warehouse_match import WarehouseMatchService
from app.services.warehouse_matching_rules import ENGINE_ID


@pytest.fixture()
def context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    session.add_all([
        User(id=1, full_name="Admin", email="engine-admin@example.com", role="admin", hashed_password="unused"),
        User(id=2, full_name="Reader", email="engine-reader@example.com", role="user", hashed_password="unused"),
    ])
    session.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: session
    try:
        with TestClient(app) as client:
            client.headers["Authorization"] = "Bearer " + create_access_token({"sub": "engine-admin@example.com"})
            yield client, session
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def post(client, path, payload):
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def flow(context):
    client, db = context
    industry = post(client, "/industries/", {"code": "ENGINE", "name": "Logistics"})
    organization = post(client, "/organizations/", {
        "org_code": "ENGINE", "legal_name": "Engine customer", "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE", "industry_id": industry["id"],
    })
    company = post(client, "/companies/", {
        "organization_id": organization["id"], "company_name": "Customer",
        "industry": industry["name"], "company_type": "Private",
    })
    lead = post(client, "/leads/", {"lead_number": "ENGINE-1", "company_id": company["id"]})
    warehouses = []
    for name, changes in [
        ("Best", {}), ("Tie", {}), ("Moderate", {"city": "Mysuru"}),
        ("Weak", {"total_area_sqft": 100}), ("Inactive", {"availability_status": "INACTIVE"}),
    ]:
        warehouses.append(post(client, "/warehouses/", {
            "warehouse_name": name, "owner_id": 1, "city": "Bengaluru", "state": "Karnataka",
            "total_area_sqft": 1000, "warehouse_type": "COVERED", "availability_status": "AVAILABLE",
            **changes,
        }))
    requirement = post(client, f"/leads/{lead['id']}/requirements/", {
        "lead_id": lead["id"], "title": "Distribution space", "minimum_area": 1000,
        "preferred_city": "Bengaluru", "preferred_state": "Karnataka",
        "warehouse_type": "COVERED", "industry": industry["name"], "requirement_status": "ACTIVE",
    })
    return client, db, requirement, warehouses


def generate(client, requirement):
    return post(client, f"/warehouse-matches/requirements/{requirement['id']}/generate", {})


def saved(client, requirement, suffix=""):
    response = client.get(f"/warehouse-matches/?requirement_id={requirement['id']}" + suffix)
    assert response.status_code == 200, response.text
    return response.json()


def test_complete_flow_idempotency_ranking_explanations_and_refresh(flow):
    client, db, requirement, warehouses = flow
    assert generate(client, requirement)["created"] == 4
    first = saved(client, requirement)
    assert [m["warehouse_id"] for m in first] == [w["id"] for w in warehouses[:4]]
    assert [m["match_rank"] for m in first] == [1, 2, 3, 4]
    assert first[0]["match_score"] > first[2]["match_score"] > first[3]["match_score"]
    assert first[0]["match_level"] == "EXCELLENT"
    assert first[3]["match_level"] == "POOR"
    for match in first:
        detail = client.get(f"/warehouse-matches/{match['id']}").json()
        assert detail == match
        reasons = json.loads(detail["match_reasons"])
        compatibility = json.loads(detail["requirement_compatibility"])
        assert len(reasons) == 4
        assert sum(r["points"] for r in reasons) + sum(a["points"] for a in compatibility["adjustments"]) == detail["match_score"]
        assert compatibility["match_level"] == detail["match_level"]
        assert any("industry" in w for w in json.loads(detail["concern_reasons"]))
    assert saved(client, requirement, "&limit=1&offset=1") == [first[1]]
    for _ in range(2):
        summary = generate(client, requirement)
        assert summary["created"] == 0 and summary["refreshed"] == 4
        assert [m["id"] for m in saved(client, requirement)] == [m["id"] for m in first]
    assert len(db.scalars(select(WarehouseMatch)).all()) == 4

    assert client.put(f"/warehouses/{warehouses[0]['id']}", json={"total_area_sqft": 50}).status_code == 200
    assert generate(client, requirement)["refreshed"] == 4
    refreshed = saved(client, requirement)
    assert refreshed[0]["warehouse_id"] == warehouses[1]["id"]
    assert next(m for m in refreshed if m["id"] == first[0]["id"])["match_score"] <= 39

    assert client.put(f"/leads/{requirement['lead_id']}/requirements/{requirement['id']}",
                      json={"minimum_area": 2000}).status_code == 200
    generate(client, requirement)
    assert all(m["match_score"] <= 39 for m in saved(client, requirement))


@pytest.mark.parametrize("status", ["OCCUPIED", "UNDER_MAINTENANCE", "INACTIVE", None])
def test_ineligible_becomes_stale_then_reactivates_same_id(flow, status):
    client, db, requirement, warehouses = flow
    generate(client, requirement)
    original = saved(client, requirement)[0]
    assert client.put(f"/warehouses/{warehouses[0]['id']}", json={"availability_status": status}).status_code == 200
    result = generate(client, requirement)
    assert result["stale"] == 1 and result["candidates_evaluated"] == 3
    match = client.get(f"/warehouse-matches/{original['id']}").json()
    assert match["status"] == "STALE" and match["match_rank"] is None
    assert match["match_score"] <= 39
    assert "no longer eligible" in json.loads(match["concern_reasons"])[0]
    assert generate(client, requirement)["created"] == 0
    assert client.put(f"/warehouses/{warehouses[0]['id']}", json={"availability_status": "AVAILABLE"}).status_code == 200
    generate(client, requirement)
    match = client.get(f"/warehouse-matches/{original['id']}").json()
    assert match["status"] == "AI_RECOMMENDED" and match["match_score"] == 100
    assert len(db.scalars(select(WarehouseMatch)).all()) == 4


@pytest.mark.parametrize("changes", [
    {"matched_by": MatchedBy.MANUAL}, {"matched_by": MatchedBy.HYBRID},
    {"model_id": "other-engine"}, {"reviewed_by_user_id": 1}, {"reviewed_at": datetime(2026, 1, 1)},
    *[{"status": status} for status in WarehouseMatchStatus if status not in (
        WarehouseMatchStatus.AI_RECOMMENDED, WarehouseMatchStatus.STALE)],
])
def test_manual_reviewed_and_progressed_matches_preserved(flow, changes):
    client, db, requirement, warehouses = flow
    match = WarehouseMatch(lead_id=requirement["lead_id"], requirement_id=requirement["id"],
                           warehouse_id=warehouses[0]["id"], match_score=12, match_rank=77,
                           status=WarehouseMatchStatus.AI_RECOMMENDED, matched_by=MatchedBy.AI,
                           model_id=ENGINE_ID, notes="Do not overwrite", match_reasons="Human evidence")
    for key, value in changes.items():
        setattr(match, key, value)
    db.add(match)
    db.commit()
    path = f"/warehouse-matches/{match.id}"
    before = client.get(path).json()
    for _ in range(2):
        summary = generate(client, requirement)
        assert summary["preserved"] == 1
        assert client.get(path).json() == before
    assert len(saved(client, requirement)) == 4


def test_generation_auth_missing_requirement_and_openapi(context):
    client, db = context
    path = "/warehouse-matches/requirements/999/generate"
    assert client.post(path).status_code == 404
    schema = client.get("/openapi.json").json()
    assert schema["paths"]["/warehouse-matches/requirements/{requirement_id}/generate"]["post"]["security"]
    client.headers.pop("Authorization")
    assert client.post(path).status_code == 401
    client.headers["Authorization"] = "Bearer invalid"
    assert client.post(path).status_code == 401
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": "engine-reader@example.com"})
    assert client.post(path).status_code == 403
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": "engine-admin@example.com"})
    db.get(User, 1).is_active = False
    db.commit()
    assert client.post(path).status_code == 401


def test_empty_generation_and_legacy_scope_preserved(flow):
    client, db, requirement, warehouses = flow
    legacy = WarehouseMatch(lead_id=requirement["lead_id"], warehouse_id=warehouses[0]["id"],
                            match_score=98, status=WarehouseMatchStatus.SHORTLISTED, matched_by=MatchedBy.MANUAL)
    db.add(legacy)
    for warehouse in db.scalars(select(Warehouse)):
        warehouse.availability_status = "INACTIVE"
    db.commit()
    result = generate(client, requirement)
    assert result["created"] == result["stale"] == result["candidates_evaluated"] == 0
    assert saved(client, requirement) == []
    assert db.get(WarehouseMatch, legacy.id).match_score == 98


def test_generation_atomic_rollback_on_failure(flow, monkeypatch):
    client, db, requirement, warehouses = flow
    service = WarehouseMatchService()
    original_commit = db.commit

    def fail_commit():
        db.flush()
        raise IntegrityError("simulated concurrent conflict", {}, Exception("conflict"))

    monkeypatch.setattr(db, "commit", fail_commit)
    with pytest.raises(IntegrityError):
        service.generate_matches_for_requirement(db, requirement["id"])
    assert db.scalars(select(WarehouseMatch)).all() == []
    response = client.post(f"/warehouse-matches/requirements/{requirement['id']}/generate")
    assert response.status_code == 409
    assert db.scalars(select(WarehouseMatch)).all() == []
    monkeypatch.setattr(db, "commit", original_commit)
    assert generate(client, requirement)["created"] == 4


def test_pending_changes_are_not_committed(flow):
    client, db, requirement, warehouses = flow
    db.get(Warehouse, warehouses[0]["id"]).warehouse_name = "Unsaved edit"
    with pytest.raises(ValueError, match="pending changes"):
        WarehouseMatchService().generate_matches_for_requirement(db, requirement["id"])
    assert db.dirty
    db.rollback()
    assert db.scalars(select(WarehouseMatch)).all() == []


def test_full_catalog_and_independent_requirements(flow):
    client, db, requirement, warehouses = flow
    db.add_all([Warehouse(warehouse_name=f"Additional {i}", owner_id=1, city="Bengaluru",
                          state="Karnataka", total_area_sqft=1000, warehouse_type="COVERED",
                          availability_status="AVAILABLE") for i in range(201)])
    db.commit()
    summary = generate(client, requirement)
    assert summary["created"] == summary["candidates_evaluated"] == 205
    assert len(saved(client, requirement, "&limit=100&offset=100")) == 100
    second = post(client, f"/leads/{requirement['lead_id']}/requirements/", {
        "lead_id": requirement["lead_id"], "title": "Other demand", "minimum_area": 2000,
    })
    assert generate(client, second)["created"] == 205
    assert generate(client, requirement)["created"] == 0
    assert len(db.scalars(select(WarehouseMatch)).all()) == 410
    assert saved(client, requirement)[0]["match_score"] == 100
    assert all(m["match_score"] <= 39 for m in saved(client, second))


def test_engine_notes_survive_refresh(flow):
    client, db, requirement, warehouses = flow
    generate(client, requirement)
    match = db.scalars(select(WarehouseMatch).order_by(WarehouseMatch.id)).first()
    match.notes = "Arrange a site visit"
    db.commit()
    match_id = match.id
    generate(client, requirement)
    assert db.get(WarehouseMatch, match_id).notes == "Arrange a site visit"