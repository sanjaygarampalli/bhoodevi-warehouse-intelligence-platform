"""Schema, service, repository, and API tests for the Industry domain."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes import router
from app.db.base import Base
from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import Industry, User
from app.repositories.industry import IndustryRepository
from app.schemas.industry import IndustryCreate, IndustryUpdate
from app.services.industry import IndustryService


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestIndustrySchema:
    @pytest.mark.parametrize("data", [
        {"code": "", "name": "Technology"},
        {"code": "   ", "name": "Technology"},
        {"code": "X" * 21, "name": "Technology"},
        {"code": "TECH", "name": "X" * 101},
        {"code": "TECH", "name": "Technology", "is_active": None},
    ])
    def test_invalid_create(self, data):
        with pytest.raises(ValidationError):
            IndustryCreate(**data)

    @pytest.mark.parametrize("field", ["code", "name", "is_active"])
    def test_update_rejects_explicit_null(self, field):
        with pytest.raises(ValidationError):
            IndustryUpdate(**{field: None})

    def test_partial_update_and_normalization(self):
        assert IndustryUpdate().model_dump(exclude_unset=True) == {}
        assert IndustryUpdate(category=None).model_dump(exclude_unset=True) == {
            "category": None
        }
        assert IndustryCreate(code=" TECH ", name=" Technology ").code == "TECH"


class TestIndustryService:
    def test_get_by_code(self, db_session):
        service = IndustryService()
        created = service.create_industry(
            db_session, IndustryCreate(code="TECH", name="Technology")
        )
        assert service.get_industry_by_code(db_session, "TECH") is created
        assert service.get_industry_by_code(db_session, "MISSING") is None

    def test_update_database_conflict_rolls_back(self, db_session, monkeypatch):
        service = IndustryService()
        first = service.create_industry(
            db_session, IndustryCreate(code="TECH", name="Technology")
        )
        second = service.create_industry(
            db_session, IndustryCreate(code="MFG", name="Manufacturing")
        )
        second_id = second.id
        monkeypatch.setattr(service, "_check_duplicates", lambda *args: None)
        with pytest.raises(ValueError, match="conflicts"):
            service.update_industry(
                db_session, second_id, IndustryUpdate(code=first.code)
            )
        assert service.get_industry_by_id(db_session, second_id).code == "MFG"
        assert service.update_industry(
            db_session, second_id, IndustryUpdate(description="Recovered")
        ).description == "Recovered"

    def test_pagination_is_ordered_by_id(self, db_session):
        db_session.add_all([
            Industry(id=20, code="A", name="First alphabetically"),
            Industry(id=10, code="Z", name="Last alphabetically"),
            Industry(id=30, code="B", name="Middle alphabetically"),
        ])
        db_session.commit()
        repository = IndustryRepository()
        assert [row.id for row in repository.get_multi(db_session)] == [10, 20, 30]
        assert [row.id for row in repository.get_multi(db_session, skip=1, limit=1)] == [20]

    def test_crud_and_repository_lookups(self, db_session):
        service = IndustryService()
        created = service.create_industry(
            db_session, IndustryCreate(code="TECH", name="Technology", category="IT")
        )
        repository = IndustryRepository()
        assert repository.get_by_code(db_session, "TECH") is created
        assert repository.get_by_name(db_session, "Technology") is created
        assert service.get_industry_by_id(db_session, created.id) is created
        assert service.list_industries(db_session) == [created]
        updated = service.update_industry(
            db_session, created.id, IndustryUpdate(category=None, is_active=False)
        )
        assert updated.category is None
        assert updated.is_active is False
        assert updated.name == "Technology"
        industry_id = created.id
        assert service.delete_industry(db_session, industry_id) is not None
        assert service.get_industry_by_id(db_session, industry_id) is None

    def test_database_conflict_rolls_back(self, db_session, monkeypatch):
        service = IndustryService()
        payload = IndustryCreate(code="TECH", name="Technology")
        service.create_industry(db_session, payload)
        monkeypatch.setattr(service, "_check_duplicates", lambda *args: None)
        with pytest.raises(ValueError, match="conflicts"):
            service.create_industry(db_session, payload)
        assert service.repository.count(db_session) == 1
        assert service.create_industry(
            db_session, IndustryCreate(code="MFG", name="Manufacturing")
        ).id is not None


class TestIndustryAPI:
    def test_get_by_code_including_inactive(self, client):
        created = client.post("/industries/", json={
            "code": "TECH", "name": "Technology", "is_active": False
        }).json()
        response = client.get("/industries/code/TECH")
        assert response.status_code == 200, response.text
        assert response.json() == created
        assert client.get("/industries/").json() == [created]
        assert client.get("/industries/code/MISSING").status_code == 404
        assert client.get(f"/industries/code/{'X' * 21}").status_code == 422
        updated = client.put(f"/industries/{created['id']}", json={
            "code": "NEW", "is_active": True
        })
        assert updated.status_code == 200, updated.text
        assert client.get("/industries/code/TECH").status_code == 404
        assert client.get("/industries/code/NEW").json() == updated.json()

    def test_crud(self, client):
        created = client.post("/industries/", json={
            "code": "TECH", "name": "Technology", "description": "IT services"
        })
        assert created.status_code == 200, created.text
        industry_id = created.json()["id"]
        assert created.json()["is_active"] is True
        assert client.get(f"/industries/{industry_id}").json()["code"] == "TECH"
        assert len(client.get("/industries/").json()) == 1
        updated = client.put(f"/industries/{industry_id}", json={
            "description": None, "is_active": False
        })
        assert updated.status_code == 200, updated.text
        assert updated.json()["description"] is None
        assert updated.json()["is_active"] is False
        assert client.delete(f"/industries/{industry_id}").status_code == 200
        assert client.get(f"/industries/{industry_id}").status_code == 404

    @pytest.mark.parametrize("duplicate", [
        {"code": "TECH", "name": "Other"},
        {"code": "OTHER", "name": "Technology"},
    ])
    def test_duplicate_create(self, client, duplicate):
        assert client.post("/industries/", json={
            "code": "TECH", "name": "Technology"
        }).status_code == 200
        assert client.post("/industries/", json=duplicate).status_code == 409

    def test_duplicate_update_and_unchanged_unique_fields(self, client):
        first = client.post("/industries/", json={
            "code": "TECH", "name": "Technology"
        }).json()
        second = client.post("/industries/", json={
            "code": "MFG", "name": "Manufacturing"
        }).json()
        assert client.put(f"/industries/{first['id']}", json={
            "code": "TECH", "name": "Technology"
        }).status_code == 200
        assert client.put(f"/industries/{second['id']}", json={
            "name": "Technology"
        }).status_code == 409
        assert client.get(f"/industries/{second['id']}").json()["name"] == "Manufacturing"

    @pytest.mark.parametrize("method", ["get", "put", "delete"])
    def test_missing(self, client, method):
        kwargs = {"json": {}} if method == "put" else {}
        assert getattr(client, method)("/industries/99999", **kwargs).status_code == 404

    def test_validation_and_pagination(self, client):
        assert client.post("/industries/", json={"code": " ", "name": "X"}).status_code == 422
        assert client.get("/industries/?skip=-1").status_code == 422
        assert client.get("/industries/?limit=101").status_code == 422
        for code in ("A", "B"):
            assert client.post("/industries/", json={"code": code, "name": code}).status_code == 200
        assert len(client.get("/industries/?skip=1&limit=1").json()) == 1

    @pytest.mark.parametrize("method,path,data", [
        ("get", "/industries/", None),
        ("get", "/industries/1", None),
        ("get", "/industries/code/TECH", None),
        ("post", "/industries/", {"code": "TECH", "name": "Technology"}),
        ("put", "/industries/1", {}),
        ("delete", "/industries/1", None),
    ])
    def test_authentication_required(self, client, method, path, data):
        client.app.dependency_overrides.pop(get_current_user)
        response = client.request(method, path, json=data)
        assert response.status_code == 401

    @pytest.mark.parametrize("method,path,data", [
        ("post", "/industries/", {"code": "TECH", "name": "Technology"}),
        ("put", "/industries/1", {}),
        ("delete", "/industries/1", None),
    ])
    def test_non_admin_cannot_write(self, client, method, path, data):
        client.app.dependency_overrides[get_current_user] = lambda: User(
            id=2, email="user@example.com", role="user"
        )
        assert client.request(method, path, json=data).status_code == 403
        assert client.get("/industries/").status_code == 200