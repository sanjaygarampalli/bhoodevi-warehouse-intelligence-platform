from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_is_a_liveness_check():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "application": "BWIP"}


def test_readiness_reports_database_availability():
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "application": "BWIP"}


def test_readiness_returns_service_unavailable_when_database_is_down():
    with patch("app.api.v1.routes.engine.connect", side_effect=RuntimeError("database unavailable")):
        response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "application": "BWIP"}