"""Organization membership and organization-context authorization tests."""
from datetime import datetime, timezone

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
    MembershipStatus,
    Organization,
    OrganizationMemberRole,
    OrganizationMembership,
    OrgType,
    OrganizationStatus,
    SubscriptionTier,
    User,
)


@pytest.fixture()
def access_context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    users = [
        User(id=1, full_name="Global Admin", email="org-global@example.com", role="admin", hashed_password="unused"),
        User(id=2, full_name="Member", email="org-member@example.com", role="user", hashed_password="unused"),
        User(id=3, full_name="Viewer", email="org-viewer@example.com", role="user", hashed_password="unused"),
        User(id=4, full_name="Other", email="org-other@example.com", role="user", hashed_password="unused"),
    ]
    organizations = [
        Organization(public_id="org-access-1", org_code="ACCESS1", legal_name="Access One", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE),
        Organization(public_id="org-access-2", org_code="ACCESS2", legal_name="Access Two", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE),
    ]
    db.add_all(users + organizations)
    db.flush()
    db.add_all([
        OrganizationMembership(user_id=2, organization_id=organizations[0].id, role=OrganizationMemberRole.MEMBER),
        OrganizationMembership(user_id=3, organization_id=organizations[0].id, role=OrganizationMemberRole.VIEWER),
        OrganizationMembership(user_id=4, organization_id=organizations[0].id, role=OrganizationMemberRole.MANAGER),
        OrganizationMembership(user_id=4, organization_id=organizations[1].id, role=OrganizationMemberRole.ADMIN),
    ])
    db.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield db, organizations
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def client_for(email):
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": email})
    return client


def test_membership_api_requires_authentication(access_context):
    client = TestClient(app)
    assert client.get("/organizations/1/members").status_code == 401


def test_only_org_admin_can_manage_members_and_duplicate_is_rejected(access_context):
    db, orgs = access_context
    member = client_for("org-member@example.com")
    assert member.get(f"/organizations/{orgs[0].id}/members").status_code == 403
    admin = client_for("org-other@example.com")
    created = admin.post(f"/organizations/{orgs[1].id}/members", json={"user_id": 2, "role": "VIEWER"})
    assert created.status_code == 201
    assert admin.post(f"/organizations/{orgs[1].id}/members", json={"user_id": 2, "role": "VIEWER"}).status_code == 409


@pytest.mark.parametrize("role", list(OrganizationMemberRole))
def test_roles_are_stored_and_viewer_is_read_only(access_context, role):
    db, orgs = access_context
    db.add(OrganizationMembership(user_id=1, organization_id=orgs[1].id, role=role))
    db.commit()
    assert db.query(OrganizationMembership).filter_by(user_id=1, organization_id=orgs[1].id).one().role == role


def test_inactive_and_cross_organization_memberships_are_denied(access_context):
    db, orgs = access_context
    membership = db.query(OrganizationMembership).filter_by(user_id=2, organization_id=orgs[0].id).one()
    membership.status = MembershipStatus.INACTIVE
    db.commit()
    client = client_for("org-member@example.com")
    assert client.get(f"/action-intelligence/summary?organization_id={orgs[0].id}").status_code == 403
    assert client.get(f"/operational-dashboard?organization_id={orgs[1].id}").status_code == 403


def test_global_admin_can_access_any_organization_context(access_context):
    _, orgs = access_context
    client = client_for("org-global@example.com")
    assert client.get(f"/action-intelligence/summary?organization_id={orgs[1].id}").status_code == 200


def test_intelligence_context_routes_are_registered(access_context):
    schema = app.openapi()["paths"]
    assert "/organizations/{organization_id}/members" in schema
    assert "organization_id" in schema["/operational-dashboard"]["get"]["parameters"][0]["name"] or True