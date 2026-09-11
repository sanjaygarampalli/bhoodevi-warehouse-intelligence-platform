"""Operational dashboard aggregation and authenticated endpoint tests."""
from datetime import datetime, timedelta, timezone

from app.models import ActivityStatus, ActivityType, FollowUpTask, LeadActivity, TaskStatus
from app.services.operational_dashboard import OperationalDashboardService
from tests.test_deal import context, post

NOW = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)


def test_empty_dashboard_is_valid(context):
    client, db = context
    dashboard = OperationalDashboardService(clock=lambda: NOW).get_dashboard(db)
    assert dashboard.executive_summary.total_active_leads == 0
    assert dashboard.executive_summary.active_deals == 0
    assert dashboard.todays_attention == []
    assert dashboard.top_priorities == []
    assert dashboard.recent_activity == []


def test_dashboard_requires_authentication(context):
    client, _ = context
    client.headers.pop("Authorization", None)
    response = client.get("/operational-dashboard")
    assert response.status_code == 401


def test_dashboard_lead_health_priority_attention_and_activity(context):
    client, db = context
    org = post(client, "/organizations/", {"org_code": "DASH", "legal_name": "Dashboard Owner", "org_type": "PVT_LTD", "subscription_tier": "FREE", "status": "ACTIVE"})
    company = post(client, "/companies/", {"organization_id": org["id"], "company_name": "Priority Prospect", "company_type": "Private", "industry": "Logistics"})
    lead = post(client, "/leads/", {"lead_number": "DASH-1", "company_id": company["id"], "status": "NEW"})
    db.add(LeadActivity(lead_id=lead["id"], activity_type=ActivityType.CALL, subject="Discovery call", activity_date=NOW.replace(tzinfo=None), status=ActivityStatus.COMPLETED))
    db.add(FollowUpTask(lead_id=lead["id"], subject="Call prospect", task_type="CALL", priority="URGENT", status=TaskStatus.OPEN.value, due_at=NOW - timedelta(days=1), created_at=NOW, updated_at=NOW))
    db.commit()

    response = client.get("/operational-dashboard?top_priorities_limit=1&recent_activity_limit=1")
    assert response.status_code == 200, response.text
    payload = response.json()
    summary = payload["executive_summary"]
    assert summary["total_active_leads"] == 1
    assert summary["new_leads"] == 1
    assert summary["overdue_follow_ups"] == 1
    assert payload["todays_attention"][0]["recommended_action"] == "FOLLOW_UP_OVERDUE"
    assert len(payload["top_priorities"]) == 1
    assert len(payload["recent_activity"]) == 1
    assert payload["lead_health"]["leads_without_requirements"] == 1


def test_dashboard_query_limits_are_validated(context):
    client, _ = context
    assert client.get("/operational-dashboard?top_priorities_limit=0").status_code == 422
    assert client.get("/operational-dashboard?recent_activity_limit=101").status_code == 422
