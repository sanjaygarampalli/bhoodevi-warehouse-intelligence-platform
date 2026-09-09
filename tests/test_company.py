"""Regression tests for Company ownership in the Industry-Organization hierarchy."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes import router
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import Company, DecisionMaker, Lead, Organization, User
from app.schemas.company import CompanyCreate
from app.schemas.organization import OrganizationCreate
from app.services.company import CompanyService
from app.services.organization import OrganizationService


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
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, full_name="Admin", email="admin@example.com", role="admin"
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def organization_payload():
    return {
        "org_code": "OWNER", "legal_name": "Company Owner", "org_type": "PVT_LTD",
        "subscription_tier": "FREE", "status": "ACTIVE",
    }


@pytest.fixture()
def company_payload():
    return {
        "company_name": "Legacy Prospect", "industry": "Manufacturing",
        "company_type": "Private",
    }


def test_company_api_ownership_lifecycle(client, company_payload, organization_payload):
    industry = client.post("/industries/", json={"code": "TECH", "name": "Technology"})
    assert industry.status_code == 200
    organization = client.post("/organizations/", json={
        **organization_payload, "industry_id": industry.json()["id"],
    })
    assert organization.status_code == 200
    organization_id = organization.json()["id"]
    response = client.post("/companies/", json={
        **company_payload, "organization_id": organization_id,
    })
    assert response.status_code == 200, response.text
    company_id = response.json()["id"]
    assert response.json()["organization_id"] == organization_id
    assert response.json()["industry"] == "Manufacturing"
    assert client.get(f"/companies/{company_id}").json()["organization_id"] == organization_id
    assert client.get("/companies/").json()[0]["organization_id"] == organization_id
    updated = client.put(f"/companies/{company_id}", json={"notes": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["organization_id"] == organization_id
    assert updated.json()["notes"] == "Updated"
    assert client.delete(f"/organizations/{organization_id}").status_code == 409
    assert client.delete(f"/industries/{industry.json()['id']}").status_code == 200
    assert client.get(f"/organizations/{organization_id}").json()["industry_id"] is None
    assert client.get(f"/companies/{company_id}").json()["industry"] == "Manufacturing"
    assert client.delete(f"/companies/{company_id}").status_code == 200
    assert client.get(f"/companies/{company_id}").status_code == 404
    assert client.delete(f"/organizations/{organization_id}").status_code == 200


@pytest.mark.parametrize("ownership", [{}, {"organization_id": None},
                                      {"organization_id": 0}, {"organization_id": -1}])
def test_company_creation_requires_valid_ownership(client, company_payload, ownership):
    response = client.post("/companies/", json={**company_payload, **ownership})
    assert response.status_code == 422, response.text


def test_company_unknown_organization(client, company_payload):
    response = client.post("/companies/", json={**company_payload, "organization_id": 99999})
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Organization not found"
    assert client.get("/companies/").json() == []


def test_company_fk_conflict_rolls_back(db_session, company_payload, organization_payload, monkeypatch):
    organization = OrganizationService().create_organization(
        db_session, OrganizationCreate(**organization_payload)
    )
    service = CompanyService()
    # Simulate a parent disappearing after reference validation; retain the real FK check.
    with monkeypatch.context() as patch:
        patch.setattr(service.organization_repository, "get_by_id", lambda *args: organization)
        with pytest.raises(ValueError, match="Company conflicts with existing data"):
            service.create_company(db_session, CompanyCreate(
                **company_payload, organization_id=99999,
            ))
    assert service.repository.count(db_session) == 0
    company = service.create_company(db_session, CompanyCreate(
        **company_payload, organization_id=organization.id,
    ))
    assert company.organization_id == organization.id


def test_company_ownership_preserves_legacy_relationships(db_session, company_payload, organization_payload):
    organization = OrganizationService().create_organization(
        db_session, OrganizationCreate(**organization_payload)
    )
    company = CompanyService().create_company(db_session, CompanyCreate(
        **company_payload, organization_id=organization.id,
    ))
    contact = DecisionMaker(company_id=company.id, full_name="Contact", designation="Director")
    lead = Lead(company_id=company.id, lead_number="OWNER-LEAD")
    db_session.add_all([contact, lead])
    db_session.commit()
    assert company.organization_owners is organization
    assert company in organization.companies
    assert contact in company.decision_makers
    assert contact.company is company
    assert lead.company is company
    assert db_session.get(Organization, organization.id) is organization
    assert db_session.get(Company, company.id).industry == "Manufacturing"