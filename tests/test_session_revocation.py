from sqlalchemy import select
from app.core.security import hash_password
from app.models import User, OrganizationMembership
from tests.test_requirement_intelligence import requirement_context, requirement_client


def login(client, email="requirement-a@example.com", password="synthetic-password"):
    result = client.post("/auth/login", data={"username": email, "password": password})
    assert result.status_code == 200, result.text
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def test_logout_revokes_old_tokens_but_new_login_works(requirement_context):
    db, _, _ = requirement_context
    db.get(User, 1).hashed_password = hash_password("synthetic-password"); db.commit()
    client = requirement_client("requirement-a@example.com")
    old = login(client)
    assert client.post("/auth/logout", headers=old).status_code == 200
    assert client.get("/auth/me", headers=old).status_code == 401
    assert client.get("/auth/me", headers=login(client)).status_code == 200


def test_password_change_revokes_and_requires_correct_current_password(requirement_context):
    db, _, _ = requirement_context
    db.get(User, 1).hashed_password = hash_password("synthetic-password"); db.commit()
    client = requirement_client("requirement-a@example.com")
    old = login(client)
    assert client.post("/auth/change-password", headers=old, json={"current_password": "wrong", "password": "new-synthetic-password"}).status_code == 400
    assert client.get("/auth/me", headers=old).status_code == 200
    assert client.post("/auth/change-password", headers=old, json={"current_password": "synthetic-password", "password": "new-synthetic-password"}).status_code == 200
    assert client.get("/auth/me", headers=old).status_code == 401
    assert client.post("/auth/login", data={"username": "requirement-a@example.com", "password": "synthetic-password"}).status_code == 401
    assert client.get("/auth/me", headers=login(client, password="new-synthetic-password")).status_code == 200


def test_only_admin_can_revoke_and_deactivation_does_not_restore_old_tokens(requirement_context):
    db, _, _ = requirement_context
    db.get(User, 3).role = "admin"; db.commit()
    member = requirement_client("requirement-a@example.com")
    assert member.post("/auth/users/2/revoke", json={}).status_code == 403
    admin = requirement_client("requirement-viewer@example.com")
    old = requirement_client("requirement-b@example.com")
    assert admin.post("/auth/users/2/revoke", json={"deactivate": True}).status_code == 200
    assert old.get("/auth/me").status_code == 401
    db.get(User, 2).is_active = True; db.commit()
    assert old.get("/auth/me").status_code == 401


def test_membership_removal_preserves_other_authorized_organization(requirement_context):
    db, orgs, reqs = requirement_context
    db.add(OrganizationMembership(user_id=1, organization_id=orgs[1].id, role="MEMBER")); db.commit()
    client = requirement_client("requirement-a@example.com")
    assert client.get(f"/requirement-intelligence/{reqs[1].id}").status_code == 200
    membership = db.scalar(select(OrganizationMembership).where(OrganizationMembership.user_id == 1, OrganizationMembership.organization_id == orgs[0].id))
    db.delete(membership); db.commit()
    assert client.get(f"/requirement-intelligence/{reqs[0].id}").status_code == 403
    assert client.get(f"/requirement-intelligence/{reqs[1].id}").status_code == 200
