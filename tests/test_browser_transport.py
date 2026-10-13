"""Bearer-only browser transport: cookies do not authenticate; CORS is exact."""
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings


def test_cors_allows_configured_origin_without_cookie_credentials():
    client = TestClient(app)
    headers = {"Origin": settings.CORS_ORIGINS[0], "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"}
    response = client.options("/auth/logout", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == settings.CORS_ORIGINS[0]
    assert "access-control-allow-credentials" not in response.headers
    headers["Origin"] = "https://untrusted.example"
    response = client.options("/auth/logout", headers=headers)
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cookie_alone_does_not_authenticate():
    client = TestClient(app)
    response = client.get("/auth/me", headers={"Cookie": "bwip_access_token=untrusted"})
    assert response.status_code == 401
