"""Real JWT routes, FK-enabled disposable SQLite, deterministic operational clock."""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers

from app.api.v1.endpoints import follow_up_task as task_api, lead as lead_api
from app.core.security import create_access_token
from app.models import Company, Deal, FollowUpTask, Lead, LeadActivity, LeadScoreSnapshot, User
from app.models.follow_up_task import TaskType, as_utc
from app.schemas.follow_up_task import (
    FollowUpTaskCreate, FollowUpTaskUpdate, NextActionTaskCreate, TaskCancellation, TaskCompletion,
)
from app.services.follow_up_task import FollowUpTaskService
from app.services.follow_up_workflow import TaskConflict, TaskNotFound
from app.services.user import UserService
from tests.test_deal import context, post

NOW = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


@pytest.fixture()
def work(context, monkeypatch):
    client, db = context
    service = FollowUpTaskService(clock=lambda: NOW)
    monkeypatch.setattr(task_api, "task_service", service)
    monkeypatch.setattr(lead_api, "task_service", service)
    org = post(client, "/organizations/", {
        "org_code": "TASK", "legal_name": "Leasing BD", "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE",
    })
    company = post(client, "/companies/", {
        "organization_id": org["id"], "company_name": "Distribution Prospect", "company_type": "Private", "industry": "",
    })
    lead = post(client, "/leads/", {"lead_number": "TASK-1", "company_id": company["id"]})
    return {"client": client, "db": db, "service": service, "org": org, "company": company, "lead": lead}


def payload(work, **changes):
    return {"lead_id": work["lead"]["id"], "subject": "Confirm warehouse demand",
            "due_at": (NOW + timedelta(days=1)).isoformat(), **changes}


def create(work, **changes):
    return post(work["client"], "/follow-up-tasks/", payload(work, **changes))


def deal_for(work, lead=None):
    client = work["client"]
    lead = lead or work["lead"]
    req = post(client, f"/leads/{lead['id']}/requirements/", {"lead_id": lead["id"], "title": "Space"})
    stages = client.get("/deal-pipeline-stages/").json()
    stage = stages[0] if stages else post(client, "/deal-pipeline-stages/", {
        "organization_id": work["org"]["id"], "stage_key": "QUALIFY", "stage_name": "Qualify", "stage_order": 10,
    })
    return post(client, "/deals/", {"deal_name": "Lease", "lead_id": lead["id"],
                                   "requirement_id": req["id"], "stage_id": stage["id"]})


def test_realistic_discover_analyze_act_complete_and_deal_workflow(work):
    client, db = work["client"], work["db"]
    lead_id = work["lead"]["id"]
    intelligence = post(client, f"/leads/{lead_id}/intelligence/calculate", {})
    assert intelligence["explanation"]["recommended_action"] == "RESEARCH_COMPANY"
    task = post(client, f"/leads/{lead_id}/next-action/task", {"due_at": payload(work)["due_at"]})
    assert task["recommendation_context"]["action_reason"] == intelligence["explanation"]["action_reason"]
    assert task["description"] == intelligence["explanation"]["action_reason"]
    assigned = client.put(f"/follow-up-tasks/{task['id']}", json={"assigned_to_user_id": 2, "status": "IN_PROGRESS"})
    assert assigned.status_code == 200
    completed = post(client, f"/follow-up-tasks/{task['id']}/complete", {"completion_notes": "Company researched"})
    assert completed["status"] == "COMPLETED"
    assert as_utc(datetime.fromisoformat(completed["completed_at"])) == NOW
    assert client.get(f"/follow-up-tasks/{task['id']}").json() == completed
    overdue = create(work, due_at=(NOW - timedelta(days=1)).isoformat())
    queue = client.get("/follow-up-tasks/?queue=OVERDUE").json()
    assert [item["id"] for item in queue] == [overdue["id"]]
    deal = deal_for(work)
    related = create(work, deal_id=deal["id"], task_type="MEETING", subject="Site visit preparation")
    configure_mappers()
    model = db.get(FollowUpTask, related["id"])
    assert model.lead.id == lead_id and model.deal.id == deal["id"]
    assert db.get(FollowUpTask, task["id"]).assigned_to_user.id == 2
    assert db.scalar(select(func.count()).select_from(LeadActivity)) == 0
    assert db.scalar(select(func.count()).select_from(LeadScoreSnapshot)) == 1
    assert db.get(Deal, deal["id"]).deal_status == "OPEN"


@pytest.mark.parametrize("task_type", list(TaskType))
def test_documented_task_types(work, task_type):
    assert create(work, task_type=task_type.value)["task_type"] == task_type.value


@pytest.mark.parametrize("changes,code", [
    ({"lead_id": 999}, 404), ({"deal_id": 999}, 404), ({"assigned_to_user_id": 999}, 404),
    ({"assigned_to_user_id": 3}, 409), ({"lead_id": 0}, 422), ({"subject": "  "}, 422),
    ({"due_at": "2026-09-09T12:00:00"}, 422), ({"due_at": None}, 422),
    ({"status": "COMPLETED"}, 422), ({"completed_at": NOW.isoformat()}, 422),
    ({"task_type": "INVENTED"}, 422), ({"priority": "INVENTED"}, 422),
    ({"recommendation_key": "RESEARCH_COMPANY"}, 422),
])
def test_creation_validation_and_recovery(work, changes, code):
    response = work["client"].post("/follow-up-tasks/", json=payload(work, **changes))
    assert response.status_code == code, response.text
    assert work["db"].scalar(select(FollowUpTask.id)) is None
    create(work)


def test_service_reference_validation_and_timezone_normalization(work):
    service, db = work["service"], work["db"]
    for changes in ({"lead_id": 999}, {"deal_id": 999}, {"assigned_to_user_id": 999}):
        with pytest.raises(TaskNotFound):
            service.create_task(db, FollowUpTaskCreate(**payload(work, **changes)))
    with pytest.raises(TaskConflict):
        service.create_task(db, FollowUpTaskCreate(**payload(work, assigned_to_user_id=3)))
    invalid = FollowUpTaskCreate.model_construct(**payload(work, subject=""))
    with pytest.raises(ValidationError):
        service.create_task(db, invalid)
    task = create(work, due_at="2026-09-09T17:30:00+05:30")
    assert as_utc(datetime.fromisoformat(task["due_at"])) == NOW
    assert not task["is_overdue"]


def test_deal_lead_and_organization_boundaries(work):
    client, db = work["client"], work["db"]
    deal = deal_for(work)
    other = post(client, "/leads/", {"lead_number": "TASK-2", "company_id": work["company"]["id"]})
    response = client.post("/follow-up-tasks/", json=payload(work, lead_id=other["id"], deal_id=deal["id"]))
    assert response.status_code == 409
    create(work, deal_id=deal["id"])
    org = post(client, "/organizations/", {
        "org_code": "OTHER", "legal_name": "Other", "org_type": "PVT_LTD", "subscription_tier": "FREE", "status": "ACTIVE",
    })
    company = db.get(Company, work["company"]["id"])
    company.organization_id = org["id"]  # Simulate an unsupported external ownership change.
    db.commit()
    assert client.post("/follow-up-tasks/", json=payload(work, deal_id=deal["id"])).status_code == 409


@pytest.mark.parametrize("terminal", ["complete", "cancel"])
def test_terminal_workflow_idempotency_and_conflicting_retries(work, terminal):
    client = work["client"]
    task = create(work)
    path = f"/follow-up-tasks/{task['id']}"
    assert client.put(path, json={"status": "IN_PROGRESS"}).status_code == 200
    assert client.put(path, json={"status": "OPEN"}).status_code == 409
    field = "completion_notes" if terminal == "complete" else "cancellation_reason"
    closed = post(client, path + "/" + terminal, {field: "Recorded outcome"})
    assert not closed["is_overdue"]
    assert post(client, path + "/" + terminal, {}) == closed
    assert post(client, path + "/" + terminal, {field: "Recorded outcome"}) == closed
    assert client.post(path + "/" + terminal, json={field: "Contradiction"}).status_code == 409
    opposite = "cancel" if terminal == "complete" else "complete"
    assert client.post(path + "/" + opposite, json={}).status_code == 409
    assert client.put(path, json={"subject": "Changed"}).status_code == 409
    assert client.put(path, json={"status": "OPEN"}).status_code == 409
    assert client.get(path).json() == closed
    assert client.delete(path).status_code == 405


@pytest.mark.parametrize("changes", [
    {"status": "COMPLETED"}, {"status": "CANCELLED"}, {"status": None}, {"due_at": None},
    {"subject": None}, {"priority": None}, {"task_type": None}, {"lead_id": 2}, {"deal_id": 2},
    {"completed_at": NOW.isoformat()}, {"recommendation_context": {}},
])
def test_generic_update_cannot_bypass_workflow(work, changes):
    task = create(work)
    assert work["client"].put(f"/follow-up-tasks/{task['id']}", json=changes).status_code == 422


def test_update_assignment_deadline_and_unassignment(work):
    task = create(work, assigned_to_user_id=2)
    client = work["client"]
    path = f"/follow-up-tasks/{task['id']}"
    for user, code in ((999, 404), (3, 409)):
        assert client.put(path, json={"assigned_to_user_id": user}).status_code == code
    updated = client.put(path, json={"assigned_to_user_id": None, "description": "Prepare call",
                                     "due_at": (NOW - timedelta(seconds=1)).isoformat(), "priority": "URGENT"})
    assert updated.status_code == 200
    assert updated.json()["is_overdue"] and updated.json()["assigned_to_user_id"] is None


@pytest.mark.parametrize("status,offset,expected", [
    ("OPEN", -1, True), ("IN_PROGRESS", -1, True), ("OPEN", 1, False),
    ("OPEN", 0, False), ("COMPLETED", -1, False), ("CANCELLED", -1, False),
])
def test_deterministic_overdue(work, status, offset, expected):
    task = create(work, due_at=(NOW + timedelta(seconds=offset)).isoformat())
    client = work["client"]
    path = f"/follow-up-tasks/{task['id']}"
    if status == "IN_PROGRESS":
        assert client.put(path, json={"status": status}).status_code == 200
    elif status in ("COMPLETED", "CANCELLED"):
        post(client, path + ("/complete" if status == "COMPLETED" else "/cancel"), {})
    assert client.get(path).json()["is_overdue"] is expected
    assert bool(client.get("/follow-up-tasks/?queue=OVERDUE").json()) is expected


def test_filters_queues_pagination_order_and_no_n_plus_one(work):
    client, db = work["client"], work["db"]
    overdue = create(work, due_at=(NOW - timedelta(days=1)).isoformat(), priority="LOW")
    urgent = create(work, due_at=overdue["due_at"], priority="URGENT", assigned_to_user_id=2)
    tied = create(work, due_at=overdue["due_at"], priority="URGENT")
    upcoming = create(work, deal_id=deal_for(work)["id"])
    closed = create(work, due_at=(NOW - timedelta(days=2)).isoformat())
    post(client, f"/follow-up-tasks/{closed['id']}/cancel", {})
    assert [t["id"] for t in client.get("/follow-up-tasks/").json()] == [urgent["id"], tied["id"], overdue["id"], closed["id"], upcoming["id"]]
    assert [t["id"] for t in client.get("/follow-up-tasks/?skip=1&limit=1").json()] == [tied["id"]]
    for filters, ids in [
        ({"assigned_to_user_id": 2}, [urgent["id"]]), ({"deal_id": upcoming["deal_id"]}, [upcoming["id"]]),
        ({"status": "CANCELLED"}, [closed["id"]]), ({"lead_id": 999}, []),
        ({"queue": "UPCOMING"}, [upcoming["id"]]),
        ({"queue": "OPEN"}, [urgent["id"], tied["id"], overdue["id"], upcoming["id"]]),
        ({"queue": "OVERDUE", "status": "CANCELLED"}, []),
    ]:
        assert [t["id"] for t in client.get("/follow-up-tasks/", params=filters).json()] == ids
    db.expire_all()
    statements = []
    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)
    event.listen(db.bind, "before_cursor_execute", capture)
    try:
        result = work["service"].list_tasks(db)
        assert len(result) == 5
        assert len(statements) == 1
    finally:
        event.remove(db.bind, "before_cursor_execute", capture)


def test_next_action_dedup_context_and_fresh_evaluation(work):
    client, db, service = work["client"], work["db"], work["service"]
    path = f"/leads/{work['lead']['id']}/next-action/task"
    body = {"due_at": payload(work)["due_at"], "assigned_to_user_id": 2}
    first = post(client, path, body)
    retry = post(client, path, {"due_at": (NOW + timedelta(days=5)).isoformat(), "assigned_to_user_id": 1})
    assert retry == first
    assert first["recommendation_context"]["missing_information"]
    assert first["recommendation_context"]["limitations"]
    assert first["recommendation_context"]["action_version"] == "v1"
    assert client.put(f"/follow-up-tasks/{first['id']}", json={"status": "IN_PROGRESS"}).status_code == 200
    assert post(client, path, body)["id"] == first["id"]
    service.complete_task(db, first["id"], TaskCompletion())
    second = post(client, path, body)
    assert second["id"] != first["id"]
    assert client.put(f"/companies/{work['company']['id']}", json={"industry": "Logistics"}).status_code == 200
    third = post(client, path, body)
    assert third["recommendation_key"] == "FIND_DECISION_MAKER"
    assert third["id"] != second["id"]
    assert client.get(f"/follow-up-tasks/{first['id']}").json()["recommendation_context"] == first["recommendation_context"]
    assert db.scalar(select(func.count()).select_from(LeadScoreSnapshot)) == 0
    assert db.scalar(select(func.count()).select_from(LeadActivity)) == 0


@pytest.mark.parametrize("status", ["WON", "LOST", "DISQUALIFIED", "DORMANT"])
def test_monitor_does_not_create_task(work, status):
    client = work["client"]
    lead_id = work["lead"]["id"]
    assert client.put(f"/leads/{lead_id}", json={"status": status}).status_code == 200
    response = client.post(f"/leads/{lead_id}/next-action/task", json={"due_at": payload(work)["due_at"]})
    assert response.status_code == 409
    assert "MONITOR" in response.text
    assert work["db"].scalar(select(FollowUpTask.id)) is None


def test_missing_resources(work):
    client = work["client"]
    for method, path, body in [
        ("get", "/follow-up-tasks/999", None), ("put", "/follow-up-tasks/999", {}),
        ("post", "/follow-up-tasks/999/complete", {}), ("post", "/follow-up-tasks/999/cancel", {}),
        ("post", "/leads/999/next-action/task", {"due_at": payload(work)["due_at"]}),
    ]:
        response = client.request(method, path, **({"json": body} if body is not None else {}))
        assert response.status_code == 404


@pytest.mark.parametrize("identity,write_code", [(None, 401), ("deal-reader@example.com", 403),
                                                   ("deal-inactive@example.com", 401)])
def test_real_jwt_permissions_on_every_route(work, identity, write_code):
    client = work["client"]
    task = create(work)
    client.headers.pop("Authorization", None)
    if identity:
        client.headers["Authorization"] = "Bearer " + create_access_token({"sub": identity})
    path = f"/follow-up-tasks/{task['id']}"
    for method, url, body in [
        ("post", "/follow-up-tasks/", payload(work)), ("put", path, {"subject": "Edit"}),
        ("post", path + "/complete", {}), ("post", path + "/cancel", {}),
        ("post", f"/leads/{work['lead']['id']}/next-action/task", {"due_at": payload(work)["due_at"]}),
    ]:
        assert client.request(method, url, json=body).status_code == write_code
    for url in (path, "/follow-up-tasks/", "/follow-up-tasks/?queue=OVERDUE"):
        assert client.get(url).status_code == (200 if write_code == 403 else 401)


def test_source_guards_preserve_completed_history(work):
    client, db = work["client"], work["db"]
    task = create(work, assigned_to_user_id=2)
    post(client, f"/follow-up-tasks/{task['id']}/complete", {})
    assert client.delete(f"/leads/{work['lead']['id']}").status_code == 409
    assert client.delete(f"/companies/{work['company']['id']}").status_code == 409
    assert client.put(f"/leads/{work['lead']['id']}", json={"company_id": 999}).status_code == 409
    with pytest.raises(TaskConflict):
        UserService().delete_user(db, db.get(User, 2))
    assert client.get(f"/follow-up-tasks/{task['id']}").json()["status"] == "COMPLETED"


def test_service_validation_pending_changes_and_failure_rollback(work, monkeypatch):
    service, db = work["service"], work["db"]
    for kwargs in ({"skip": -1}, {"limit": 101}, {"queue": "BAD"}, {"status": "BAD"}, {"lead_id": 0}):
        with pytest.raises(TaskConflict):
            service.list_tasks(db, **kwargs)
    lead = db.get(Lead, work["lead"]["id"])
    lead.lead_number = "UNCOMMITTED"
    with pytest.raises(TaskConflict, match="pending changes"):
        service.create_task(db, FollowUpTaskCreate(**payload(work)))
    assert lead in db.dirty
    db.rollback()
    task = create(work)
    original = service.repository.save
    def fail(db, task):
        db.flush()
        raise RuntimeError("Simulated persistence failure")
    monkeypatch.setattr(service.repository, "save", fail)
    with pytest.raises(RuntimeError):
        service.complete_task(db, task["id"], TaskCompletion())
    assert db.get(FollowUpTask, task["id"]).status == "OPEN"
    assert db.get(FollowUpTask, task["id"]).completed_at is None
    monkeypatch.setattr(service.repository, "save", original)
    service.cancel_task(db, task["id"], TaskCancellation())


def test_database_active_recommendation_constraint(work):
    service, db = work["service"], work["db"]
    data = NextActionTaskCreate(due_at=NOW)
    first = service.create_from_next_action(db, work["lead"]["id"], data)
    duplicate = FollowUpTask(lead_id=first.lead_id, subject="Duplicate", due_at=NOW,
                             recommendation_key=first.recommendation_key, status="IN_PROGRESS")
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    service.cancel_task(db, first.id, TaskCancellation())
    assert service.create_from_next_action(db, first.lead_id, data).id != first.id