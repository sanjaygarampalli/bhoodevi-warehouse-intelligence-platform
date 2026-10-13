"""Authorized detail responses must exercise commercial data and response serialization."""
from app.models import OrganizationMembership, OrganizationMemberRole, User, Lead, Requirement
from tests.test_company_intelligence_foundation import isolated_company_api


def permit_viewer(db, client, company):
    user = db.query(User).filter_by(email="org-b-user@example.com").one()
    db.add(OrganizationMembership(user_id=user.id, organization_id=company.organization_id, role=OrganizationMemberRole.VIEWER))
    db.commit()


def test_authorized_decision_maker_detail_serializes_priority_and_contact_methods(isolated_company_api):
    db, client, company, *_ = isolated_company_api
    permit_viewer(db, client, company)
    response = client.get(f"/companies/{company.id}/decision-maker-priorities")
    assert response.status_code == 200
    result = response.json()
    assert result["prospect_priority"]["company_id"] == company.id
    assert result["contacts"][0]["contact"]["methods"][0]["value"] == "a@example.com"
    assert result["human_review_required"] is True


def test_commercial_detail_uses_requirement_status_and_excludes_closed_records(isolated_company_api):
    db, client, company, *_ = isolated_company_api
    permit_viewer(db, client, company)
    lead = Lead(company_id=company.id, lead_number="SYNTHETIC-ACTIVE")
    closed = Lead(company_id=company.id, lead_number="SYNTHETIC-CLOSED", status="LOST")
    db.add_all([lead, closed]); db.flush()
    active = Requirement(lead_id=lead.id, title="Synthetic active", requirement_status="ACTIVE")
    inactive = Requirement(lead_id=lead.id, title="Synthetic closed", requirement_status="CLOSED")
    foreign_pipeline = Requirement(lead_id=closed.id, title="Synthetic closed lead", requirement_status="ACTIVE")
    db.add_all([active, inactive, foreign_pipeline]); db.commit()
    response = client.get(f"/companies/{company.id}/commercial-context")
    assert response.status_code == 200
    result = response.json()
    assert result["active_lead_ids"] == [lead.id]
    assert result["active_requirement_ids"] == [active.id]
    assert result["context"] == "ACTIVE_REQUIREMENT"
    assert db.query(Lead).count() == 2
    assert db.query(Requirement).count() == 3
