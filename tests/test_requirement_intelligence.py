from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    Company,
    Lead,
    Organization,
    OrganizationMemberRole,
    OrganizationMembership,
    OrgType,
    OrganizationStatus,
    Requirement,
    SubscriptionTier,
    User,
)


@pytest.fixture()
def requirement_context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    users = [
        User(id=1, full_name="Requirement A", email="requirement-a@example.com", role="user", hashed_password="unused"),
        User(id=2, full_name="Requirement B", email="requirement-b@example.com", role="user", hashed_password="unused"),
        User(id=3, full_name="Requirement Viewer", email="requirement-viewer@example.com", role="user", hashed_password="unused"),
    ]
    organizations = [
        Organization(public_id="requirement-org-a", org_code="REQA", legal_name="Requirement Organization A", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE),
        Organization(public_id="requirement-org-b", org_code="REQB", legal_name="Requirement Organization B", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE),
    ]
    db.add_all(users + organizations)
    db.flush()
    companies = [
        Company(organization_id=organizations[0].id, company_name="Demand A", industry="Logistics", company_type="Private"),
        Company(organization_id=organizations[1].id, company_name="Demand B", industry="Manufacturing", company_type="Private"),
    ]
    db.add_all(companies)
    db.flush()
    leads = [Lead(lead_number="REQ-A-1", company_id=companies[0].id), Lead(lead_number="REQ-B-1", company_id=companies[1].id)]
    db.add_all(leads)
    db.flush()
    requirements = [
        Requirement(lead_id=leads[0].id, title="A distribution requirement", preferred_city="Bengaluru", minimum_area=10000),
        Requirement(lead_id=leads[1].id, title="B private requirement"),
    ]
    db.add_all(requirements)
    db.flush()
    db.add_all([
        OrganizationMembership(user_id=1, organization_id=organizations[0].id, role=OrganizationMemberRole.MEMBER),
        OrganizationMembership(user_id=2, organization_id=organizations[1].id, role=OrganizationMemberRole.MEMBER),
        OrganizationMembership(user_id=3, organization_id=organizations[0].id, role=OrganizationMemberRole.VIEWER),
    ])
    db.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield db, organizations, requirements
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def requirement_client(email: str):
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": email})
    return client


def evidence_payload(**overrides):
    payload = {
        "source": "Customer discovery call",
        "source_type": "CALL",
        "observed_evidence": "Customer requested 10,000 sq ft near Bengaluru.",
        "inference": "Potential near-term warehouse requirement.",
        "classification": "FACT",
        "evidence_date": datetime.utcnow().isoformat(),
        "confidence": 92,
    }
    payload.update(overrides)
    return payload


def test_requirement_intelligence_is_tenant_scoped_and_missing_is_not_found(requirement_context):
    _, organizations, requirements = requirement_context
    member = requirement_client("requirement-a@example.com")
    assert member.get(f"/requirement-intelligence?organization_id={organizations[0].id}").status_code == 200
    assert len(member.get(f"/requirement-intelligence?organization_id={organizations[0].id}").json()) == 1
    assert member.get(f"/requirement-intelligence?organization_id={organizations[1].id}").status_code == 403
    assert member.get(f"/requirement-intelligence/{requirements[1].id}").status_code == 403
    assert member.get("/requirement-intelligence/999999").status_code == 404


def test_requirement_evidence_requires_write_membership_and_protects_verified_content(requirement_context):
    _, organizations, requirements = requirement_context
    member = requirement_client("requirement-a@example.com")
    viewer = requirement_client("requirement-viewer@example.com")
    evidence_url = f"/requirement-intelligence/{requirements[0].id}/evidence"
    assert viewer.post(evidence_url, json=evidence_payload()).status_code == 403
    created = member.post(evidence_url, json=evidence_payload())
    assert created.status_code == 201
    evidence_id = created.json()["id"]
    assert created.json()["classification"] == "FACT"
    assert member.post(evidence_url, json=evidence_payload(verification_status="VERIFIED")).status_code == 409
    assert member.patch(f"{evidence_url}/{evidence_id}", json={"verification_status": "REVIEWED"}).status_code == 200
    assert member.patch(f"{evidence_url}/{evidence_id}", json={"verification_status": "VERIFIED"}).status_code == 200
    assert member.patch(f"{evidence_url}/{evidence_id}", json={"observed_evidence": "Changed after verification"}).status_code == 409


def test_requirement_assessment_preserves_unknown_and_stale_freshness(requirement_context):
    _, organizations, requirements = requirement_context
    member = requirement_client("requirement-a@example.com")
    assessment_url = f"/requirement-intelligence/{requirements[0].id}/assessment"
    initial = member.get(assessment_url)
    assert initial.status_code == 200
    assert initial.json()["freshness"] == "UNKNOWN"
    member.post(f"/requirement-intelligence/{requirements[0].id}/evidence", json=evidence_payload(evidence_date=(datetime.utcnow() - timedelta(days=120)).isoformat()))
    stale = member.get(assessment_url)
    assert stale.status_code == 200
    assert stale.json()["freshness"] == "STALE"

@pytest.mark.parametrize("method,suffix,payload", [
    ("get", "", None), ("get", "/evidence", None), ("get", "/assessment", None),
    ("post", "/evidence", {"source": "QA", "observed_evidence": "QA", "classification": "UNKNOWN"}),
])
def test_requirement_paths_require_authentication(requirement_context, method, suffix, payload):
    _, _, requirements = requirement_context
    response = TestClient(app).request(method, f"/requirement-intelligence/{requirements[0].id}{suffix}", json=payload)
    assert response.status_code == 401


@pytest.mark.parametrize("field", ["source", "observed_evidence", "classification", "verification_status"])
def test_evidence_required_fields_reject_explicit_null(requirement_context, field):
    _, _, requirements = requirement_context
    client = requirement_client("requirement-a@example.com")
    url = f"/requirement-intelligence/{requirements[0].id}/evidence"
    evidence = client.post(url, json=evidence_payload()).json()
    assert client.patch(f"{url}/{evidence['id']}", json={field: None}).status_code == 422
    assert client.get(url).json()[0][field] == evidence[field]


def test_evidence_wrong_same_org_parent_is_hidden(requirement_context):
    db, _, requirements = requirement_context
    other = Requirement(lead_id=requirements[0].lead_id, title="Other same-organization demand")
    db.add(other); db.commit()
    client = requirement_client("requirement-a@example.com")
    evidence = client.post(f"/requirement-intelligence/{other.id}/evidence", json=evidence_payload()).json()
    response = client.patch(f"/requirement-intelligence/{requirements[0].id}/evidence/{evidence['id']}", json={"notes": "Wrong parent"})
    assert response.status_code == 404
    assert client.get(f"/requirement-intelligence/{other.id}/evidence").json()[0]["notes"] is None


def test_inactive_membership_and_global_admin_policy(requirement_context):
    from app.models import MembershipStatus
    db, organizations, requirements = requirement_context
    membership = db.query(OrganizationMembership).filter_by(user_id=1).one()
    membership.status = MembershipStatus.INACTIVE
    db.commit()
    client = requirement_client("requirement-a@example.com")
    assert client.get(f"/requirement-intelligence/{requirements[0].id}").status_code == 403
    assert client.post(f"/requirement-intelligence/{requirements[0].id}/evidence", json=evidence_payload()).status_code == 403
    admin = User(full_name="QA Admin", email="qa-admin@example.com", role="admin", hashed_password="unused")
    db.add(admin); db.commit()
    client = requirement_client(admin.email)
    assert client.get(f"/requirement-intelligence?organization_id={organizations[0].id}").status_code == 200
    assert client.post(f"/requirement-intelligence/{requirements[0].id}/evidence", json=evidence_payload()).status_code == 201


def test_timezone_rejected_freshness_and_review_gate(requirement_context):
    _, _, requirements = requirement_context
    client = requirement_client("requirement-a@example.com")
    url = f"/requirement-intelligence/{requirements[0].id}/evidence"
    created = client.post(url, json=evidence_payload(evidence_date="2020-01-01T12:00:00+05:30"))
    assert created.status_code == 201
    assert created.json()["evidence_date"].startswith("2020-01-01T06:30:00")
    evidence_id = created.json()["id"]
    assert client.patch(f"{url}/{evidence_id}", json={"verification_status": "VERIFIED"}).status_code == 409
    client.post(url, json=evidence_payload(verification_status="REJECTED"))
    assessment = client.get(f"/requirement-intelligence/{requirements[0].id}/assessment")
    assert assessment.status_code == 200
    assert assessment.json()["freshness"] == "STALE"


def test_requirement_search_status_and_unlinked_provenance(requirement_context):
    _, organizations, requirements = requirement_context
    client = requirement_client("requirement-a@example.com")
    url = f"/requirement-intelligence?organization_id={organizations[0].id}"
    assert client.get(url + "&query=distribution").json()[0]["requirement"]["id"] == requirements[0].id
    assert client.get(url + "&query=nonexistent").json() == []
    assert client.get(url + "&status=CLOSED").json() == []
    assert client.get(url).json()[0]["market_signal_ids"] == []
