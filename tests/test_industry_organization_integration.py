"""Industry and Organization wiring through the real application."""

from collections import Counter

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import configure_mappers, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_current_user
from app.main import app
from app.models import Company, Industry, Organization, User


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys = ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    previous_overrides = app.dependency_overrides.copy()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, email="admin@example.com", role="admin"
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


DOMAIN_ROUTES = {
    "/industries/": {"get", "post"},
    "/industries/{industry_id}": {"get", "put", "delete"},
    "/industries/code/{code}": {"get"},
    "/organizations/": {"get", "post"},
    "/organizations/{organization_id}": {"get", "put", "delete"},
    "/organizations/code/{org_code}": {"get"},
    "/organizations/public-id/{public_id}": {"get"},
}


def test_real_app_registration_and_openapi(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path, methods in DOMAIN_ROUTES.items():
        assert set(paths[path]) == methods
        for method in methods:
            if method != "delete":
                schema = paths[path][method]["responses"]["200"]["content"][
                    "application/json"
                ]["schema"]
                expected = "IndustryResponse" if path.startswith("/industries") else "OrganizationResponse"
                if method == "get" and path.endswith("/"):
                    schema = schema["items"]
                assert schema["$ref"] == f"#/components/schemas/{expected}"

    def domain_operations(router):
        for route in router.routes:
            if isinstance(route, APIRoute) and route.path in DOMAIN_ROUTES:
                yield from ((route.path, method.lower()) for method in route.methods)
            # FastAPI can retain included routers lazily instead of flattening routes.
            elif hasattr(route, "original_router"):
                yield from domain_operations(route.original_router)

    counts = Counter(domain_operations(app.router))
    assert counts == Counter({
        (path, method): 1 for path, methods in DOMAIN_ROUTES.items() for method in methods
    })


def test_real_app_hierarchy_and_lookups(client):
    response = client.post("/industries/", json={"code": "TECH", "name": "Technology"})
    assert response.status_code == 200, response.text
    industry = response.json()
    response = client.post("/organizations/", json={
        "org_code": "OWNER", "legal_name": "Owner", "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE", "industry_id": industry["id"],
    })
    assert response.status_code == 200, response.text
    organization = response.json()
    response = client.post("/companies/", json={
        "organization_id": organization["id"], "company_name": "Prospect",
        "industry": "Manufacturing", "company_type": "Private",
    })
    assert response.status_code == 200, response.text
    company = response.json()
    assert client.get("/industries/code/TECH").json() == industry
    public_path = f"/organizations/public-id/{organization['public_id']}"
    assert client.get(public_path).json() == organization
    assert client.get("/organizations/code/OWNER").json() == organization
    assert organization["industry"] == industry
    assert client.delete(f"/organizations/{organization['id']}").status_code == 409
    assert client.delete(f"/industries/{industry['id']}").status_code == 200
    remaining = client.get(public_path).json()
    assert remaining["industry_id"] is None
    assert remaining["industry"] is None
    assert client.get(f"/companies/{company['id']}").json() == company
    assert client.delete(f"/companies/{company['id']}").status_code == 200
    assert client.delete(f"/organizations/{organization['id']}").status_code == 200


@pytest.mark.parametrize("path", [
    "/industries/", "/industries/1", "/industries/code/TECH",
    "/organizations/", "/organizations/1", "/organizations/code/OWNER",
    "/organizations/public-id/00000000-0000-0000-0000-000000000000",
])
def test_real_app_read_authentication(client, path):
    app.dependency_overrides.pop(get_current_user)
    assert client.get(path).status_code == 401


def test_hierarchy_mappers():
    configure_mappers()
    assert Organization.industry.property.mapper.class_ is Industry
    assert Organization.companies.property.mapper.class_ is Company
    assert Company.organization_owners.property.mapper.class_ is Organization
    assert Organization.companies.property.back_populates == "organization_owners"
    assert Company.organization_owners.property.back_populates == "companies"