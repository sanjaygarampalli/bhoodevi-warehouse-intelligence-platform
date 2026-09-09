"""Cross-layer regressions with real authentication and enforced foreign keys."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes import router
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models import Company, Lead, MoveInTimeframe, Organization, Requirement, User


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin(db_session):
    user = User(
        full_name="Audit Admin", email="audit@example.com", role="admin",
        hashed_password=hash_password("audit-password"), is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


def login(client, email="audit@example.com"):
    return client.post("/auth/login", data={
        "username": email, "password": "audit-password",
    })


@pytest.fixture()
def authenticated_client(client, admin):
    response = login(client)
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


@pytest.fixture()
def leads(db_session):
    organization = Organization(
        public_id="audit-organization", org_code="AUDIT", legal_name="Audit Tenant",
        org_type="PVT_LTD", subscription_tier="FREE", status="ACTIVE",
    )
    db_session.add(organization)
    db_session.flush()
    company = Company(
        organization_id=organization.id, company_name="Audit Company",
        industry="Manufacturing", company_type="Private",
    )
    db_session.add(company)
    db_session.flush()
    records = [Lead(company_id=company.id, lead_number=f"AUDIT-{i}") for i in (1, 2)]
    db_session.add_all(records)
    db_session.commit()
    return records


def test_public_registration_cannot_grant_admin(client, db_session):
    response = client.post("/auth/register", json={
        "full_name": "Public User", "email": "public@example.com",
        "password": "audit-password", "role": "admin",
    })
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "user"
    assert db_session.query(User).filter_by(email="public@example.com").one().role == "user"
    token = login(client, "public@example.com")
    assert token.status_code == 200
    headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
    assert client.get("/industries/", headers=headers).status_code == 200
    assert client.post("/industries/", headers=headers, json={
        "code": "NOADMIN", "name": "No privilege escalation",
    }).status_code == 403
    assert client.post("/organizations/", headers=headers, json={
        "org_code": "NOADMIN", "legal_name": "No privilege escalation",
        "org_type": "PVT_LTD", "subscription_tier": "FREE", "status": "ACTIVE",
    }).status_code == 403


def test_inactive_user_cannot_login(client, db_session, admin):
    admin.is_active = False
    db_session.commit()
    assert login(client).status_code == 401


@pytest.mark.parametrize("path", ["/industries/", "/organizations/", "/companies/"])
def test_deactivated_user_cannot_reuse_token(authenticated_client, db_session, admin, path):
    admin.is_active = False
    db_session.commit()
    assert authenticated_client.get(path).status_code == 401


@pytest.mark.parametrize("model", [Lead, Requirement])
@pytest.mark.parametrize("value", list(MoveInTimeframe))
def test_timeframe_matches_postgresql_enum_labels(model, value):
    enum_type = model.__table__.c.move_in_timeframe.type
    dialect = postgresql.dialect()
    assert enum_type.enums == [item.value for item in MoveInTimeframe]
    assert enum_type.bind_processor(dialect)(value) == value.value
    assert enum_type.result_processor(dialect, None)(value.value) is value


@pytest.mark.parametrize("model", [Lead, Requirement])
def test_timeframe_database_round_trip(db_session, leads, model):
    if model is Lead:
        record = leads[0]
    else:
        record = Requirement(lead_id=leads[0].id, title="Enum round trip")
        db_session.add(record)
    record.move_in_timeframe = MoveInTimeframe.ONE_TO_THREE_MONTHS
    db_session.commit()
    record_id = record.id
    assert db_session.execute(text(
        f"SELECT move_in_timeframe FROM {model.__tablename__} WHERE id = :id"
    ), {"id": record_id}).scalar_one() == "1_3_MONTHS"
    db_session.expire_all()
    assert db_session.get(model, record_id).move_in_timeframe is MoveInTimeframe.ONE_TO_THREE_MONTHS


@pytest.mark.parametrize("resource,payload", [
    ("activities", {"activity_type": "NOTE", "subject": "Original"}),
    ("requirements", {"title": "Original"}),
])
@pytest.mark.parametrize("method", ["put", "delete"])
def test_nested_mutation_checks_parent(authenticated_client, leads, resource, payload, method):
    client = authenticated_client
    parent, other = leads
    created = client.post(f"/leads/{parent.id}/{resource}/", json={
        **payload, "lead_id": parent.id,
    })
    assert created.status_code == 200, created.text
    record_id = created.json()["id"]
    path = f"/leads/{parent.id}/{resource}/{record_id}"
    wrong_path = f"/leads/{other.id}/{resource}/{record_id}"
    assert client.get(wrong_path).status_code == 404
    kwargs = {"json": {"description": "Wrong parent"}} if method == "put" else {}
    assert client.request(method, wrong_path, **kwargs).status_code == 404
    unchanged = client.get(path)
    assert unchanged.status_code == 200
    assert unchanged.json()["description"] is None
    assert client.request(method, path, **kwargs).status_code == 200


@pytest.mark.parametrize("resource,payload", [
    ("activities", {"activity_type": "NOTE", "subject": "Original"}),
    ("requirements", {"title": "Original"}),
])
def test_nested_update_rejects_conflicting_body_parent(authenticated_client, leads, resource, payload):
    client = authenticated_client
    parent, other = leads
    created = client.post(f"/leads/{parent.id}/{resource}/", json={
        **payload, "lead_id": parent.id,
    })
    assert created.status_code == 200
    path = f"/leads/{parent.id}/{resource}/{created.json()['id']}"
    assert client.put(path, json={"lead_id": other.id}).status_code == 400
    assert client.get(path).json()["lead_id"] == parent.id
    assert client.put(path, json={"lead_id": parent.id}).status_code == 200