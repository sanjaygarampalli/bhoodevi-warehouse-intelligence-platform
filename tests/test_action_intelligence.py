"""Action queue behavior through the existing JWT and SQLite test fixture."""

from datetime import datetime, timedelta, timezone

from app.models import FollowUpTask, TaskStatus
from app.services.action_intelligence import ActionIntelligenceService
from tests.test_deal import context, post

NOW = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)


def test_empty_action_queue_and_summary(context):
    client, db = context
    service = ActionIntelligenceService(clock=lambda: NOW)
    summary = service.get_action_summary(db)
    assert summary.total_actions == 0
    assert client.get("/action-intelligence/summary").status_code == 200
    assert client.get("/action-intelligence/actions").json()["items"] == []


def test_action_endpoints_require_authentication(context):
    client, _ = context
    client.headers.pop("Authorization", None)
    assert client.get("/action-intelligence/actions").status_code == 401


def test_overdue_follow_up_is_single_critical_action(context):
    client, db = context
    org = post(client, "/organizations/", {"org_code": "ACT", "legal_name": "Action Owner", "org_type": "PVT_LTD", "subscription_tier": "FREE", "status": "ACTIVE"})
    company = post(client, "/companies/", {"organization_id": org["id"], "company_name": "Action Prospect", "company_type": "Private", "industry": "Logistics"})
    lead = post(client, "/leads/", {"lead_number": "ACT-1", "company_id": company["id"]})
    db.add(FollowUpTask(lead_id=lead["id"], subject="Call today", task_type="CALL", priority="HIGH", status=TaskStatus.OPEN.value, due_at=NOW - timedelta(days=1), created_at=NOW, updated_at=NOW))
    db.commit()

    service = ActionIntelligenceService(clock=lambda: NOW)
    result = service.get_prioritized_actions(db, limit=20)
    assert len(result.items) == 1
    assert result.items[0].action_type.value == "FOLLOW_UP_OVERDUE"
    assert result.items[0].priority.value == "CRITICAL"
    assert service.get_action_summary(db).overdue_follow_ups == 1


def test_today_is_bounded_and_lead_filter_works(context):
    client, db = context
    org = post(client, "/organizations/", {"org_code": "ACT2", "legal_name": "Action Owner 2", "org_type": "PVT_LTD", "subscription_tier": "FREE", "status": "ACTIVE"})
    company = post(client, "/companies/", {"organization_id": org["id"], "company_name": "Action Prospect 2", "company_type": "Private", "industry": "Logistics"})
    lead = post(client, "/leads/", {"lead_number": "ACT-2", "company_id": company["id"]})
    response = client.get("/action-intelligence/today?limit=1")
    assert response.status_code == 200
    assert response.json()["limit"] == 1
    lead_response = client.get(f"/action-intelligence/leads/{lead['id']}?limit=1")
    assert lead_response.status_code == 200
    assert all(item["lead_id"] == lead["id"] for item in lead_response.json()["items"])
    assert client.get("/action-intelligence/today?limit=0").status_code == 422


def test_dashboard_surfaces_action_summary(context):
    client, db = context
    org = post(client, "/organizations/", {"org_code": "ACT3", "legal_name": "Action Owner 3", "org_type": "PVT_LTD", "subscription_tier": "FREE", "status": "ACTIVE"})
    company = post(client, "/companies/", {"organization_id": org["id"], "company_name": "Action Prospect 3", "company_type": "Private", "industry": "Logistics"})
    lead = post(client, "/leads/", {"lead_number": "ACT-3", "company_id": company["id"]})
    db.add(FollowUpTask(lead_id=lead["id"], subject="Overdue", task_type="CALL", priority="URGENT", status=TaskStatus.OPEN.value, due_at=NOW - timedelta(hours=1), created_at=NOW, updated_at=NOW))
    db.commit()
    dashboard = client.get("/operational-dashboard").json()
    assert dashboard["executive_summary"]["overdue_actions"] == 1