from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.core import rate_limit


def test_auth_limit_returns_429_recovers_and_ignores_spoofed_headers(monkeypatch):
    time = [0]
    limiter = rate_limit.FixedWindowLimiter(2, 60, clock=lambda: time[0])
    monkeypatch.setattr(rate_limit, "auth_limiter", limiter)
    app = FastAPI()
    @app.post("/login", dependencies=[Depends(rate_limit.require_auth_rate_limit)])
    def login():
        return {"synthetic": True}
    client = TestClient(app)
    assert client.post("/login").status_code == 200
    assert client.post("/login").status_code == 200
    limited = client.post("/login", headers={"X-Forwarded-For": "1.2.3.4"})
    assert limited.status_code == 429
    assert "Retry-After" in limited.headers
    time[0] = 60
    assert client.post("/login").status_code == 200


def test_auth_limit_memory_is_bounded_without_evicting_active_clients():
    limiter = rate_limit.FixedWindowLimiter(1, 60, capacity=2, clock=lambda: 0)
    assert limiter.allow("a") and limiter.allow("b")
    assert not limiter.allow("c")
    assert not limiter.allow("a")
    assert len(limiter.entries) == 2
