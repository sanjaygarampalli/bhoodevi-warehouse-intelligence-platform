"""Synthetic identity tests; no calls to real Google or customer databases."""
import hashlib
import time

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.models import GoogleLoginChallenge, User
from app.services import google_auth
from tests.test_requirement_intelligence import requirement_client, requirement_context


@pytest.fixture()
def google_context(requirement_context, monkeypatch):
    db, orgs, reqs = requirement_context
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "synthetic.apps.googleusercontent.com")
    db.get(User, 1).hashed_password = hash_password("synthetic-password")
    db.commit()
    client = requirement_client("requirement-a@example.com")
    client.headers.pop("Authorization")
    client.headers["Origin"] = settings.CORS_ORIGINS[0]
    return db, client, orgs, reqs


def attempt(client, monkeypatch, *, subject="synthetic-google-subject", email="requirement-a@example.com", password=None, **changes):
    challenge = client.post("/auth/google/challenge")
    assert challenge.status_code == 200, challenge.text
    nonce = challenge.json()["nonce"]
    claims = {"sub": subject, "email": email, "email_verified": True, "nonce": nonce, **changes}
    monkeypatch.setattr(google_auth, "verify_google_credential", lambda credential: claims)
    payload = {"credential": "synthetic-credential", "nonce": nonce}
    if password is not None:
        payload["link_password"] = password
    return client.post("/auth/google", json=payload), payload


def test_explicit_link_and_returning_identity_preserve_tenant_scope_and_revocation(google_context, monkeypatch):
    db, client, orgs, reqs = google_context
    linked, _ = attempt(client, monkeypatch, password="synthetic-password")
    assert linked.status_code == 200, linked.text
    assert db.scalar(select(User.google_subject).where(User.id == 1)) == "synthetic-google-subject"
    headers = {"Authorization": "Bearer " + linked.json()["access_token"]}
    assert client.get(f"/requirement-intelligence/{reqs[0].id}", headers=headers).status_code == 200
    assert client.get(f"/requirement-intelligence/{reqs[1].id}", headers=headers).status_code == 403
    assert client.post("/auth/logout", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401
    # Stable Google subject wins; changed provider email does not rename or merge BWIP accounts.
    returning, _ = attempt(client, monkeypatch, email="changed-provider@example.com")
    assert returning.status_code == 200
    assert db.get(User, 1).email == "requirement-a@example.com"
    fresh = {"Authorization": "Bearer " + returning.json()["access_token"]}
    assert client.get("/auth/me", headers=fresh).status_code == 200


@pytest.mark.parametrize("password", [None, "wrong-password"])
def test_email_match_alone_never_links_an_existing_account(google_context, monkeypatch, password):
    db, client, _, _ = google_context
    result, payload = attempt(client, monkeypatch, password=password)
    assert result.status_code == 409
    assert db.get(User, 1).google_subject is None
    assert client.post("/auth/google", json=payload).status_code == 401


def test_unknown_google_identity_does_not_create_an_account(google_context, monkeypatch):
    db, client, _, _ = google_context
    before = len(db.scalars(select(User)).all())
    result, _ = attempt(client, monkeypatch, email="unregistered@example.com")
    assert result.status_code == 403
    assert len(db.scalars(select(User)).all()) == before


@pytest.mark.parametrize("changes", [{"email_verified": False}, {"email_verified": "true"}, {"nonce": "wrong"}, {"sub": ""}])
def test_reject_unverified_or_mismatched_claims(google_context, monkeypatch, changes):
    _, client, _, _ = google_context
    result, _ = attempt(client, monkeypatch, **changes)
    assert result.status_code == 401


def test_expired_challenge_and_replayed_success_fail(google_context, monkeypatch):
    db, client, _, _ = google_context
    good, payload = attempt(client, monkeypatch, password="synthetic-password")
    assert good.status_code == 200
    assert client.post("/auth/google", json=payload).status_code == 401
    db.add(GoogleLoginChallenge(nonce_hash=hashlib.sha256(payload["nonce"].encode()).hexdigest(), expires_at=int(time.time())-1))
    db.commit()
    assert client.post("/auth/google", json=payload).status_code == 401


def test_inactive_and_differently_linked_accounts_are_denied(google_context, monkeypatch):
    db, client, _, _ = google_context
    db.get(User, 1).google_subject = "different-google-subject"
    db.commit()
    denied, _ = attempt(client, monkeypatch, password="synthetic-password")
    assert denied.status_code == 403
    db.get(User, 1).is_active = False
    db.commit()
    denied, _ = attempt(client, monkeypatch, subject="different-google-subject")
    assert denied.status_code == 403


def test_disabled_origin_and_oversized_inputs_fail_closed(google_context, monkeypatch):
    _, client, _, _ = google_context
    assert client.post("/auth/google/challenge", headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/auth/google", json={"credential": "x"*8193, "nonce": "a"*43}).status_code == 422
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "")
    assert client.get("/auth/google/config").json() == {"client_id": None}
    assert client.post("/auth/google/challenge").status_code == 503


def test_invalid_signature_or_provider_outage_never_creates_session(google_context, monkeypatch):
    db, client, _, _ = google_context
    nonce = client.post("/auth/google/challenge").json()["nonce"]
    for status in (401, 503):
        def fail(_credential):
            raise HTTPException(status, "Synthetic verification failure")
        monkeypatch.setattr(google_auth, "verify_google_credential", fail)
        result = client.post("/auth/google", json={"credential": "invalid", "nonce": nonce})
        assert result.status_code == status and "access_token" not in result.json()
    assert db.get(User, 1).google_subject is None


@pytest.mark.parametrize("invalid", [None, "audience", "issuer", "expired", "signature"])
def test_official_google_library_checks_signed_tokens(monkeypatch, invalid):
    """Real RSA verification against a synthetic key; the network transport alone is mocked."""
    import json
    import rsa
    from google.auth import crypt, jwt as google_jwt
    from google.auth.transport.requests import Request

    public, private = rsa.newkeys(2048)
    signer = crypt.RSASigner.from_string(private.save_pkcs1(), key_id="synthetic-key")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "synthetic.apps.googleusercontent.com")
    now = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": settings.GOOGLE_CLIENT_ID,
              "sub": "synthetic-subject", "email": "synthetic@example.com", "email_verified": True,
              "nonce": "synthetic-nonce", "iat": now - 60, "exp": now + 300}
    if invalid == "audience": claims["aud"] = "another-client.apps.googleusercontent.com"
    if invalid == "issuer": claims["iss"] = "https://evil.example"
    if invalid == "expired": claims["exp"] = now - 1
    if invalid == "signature": public, _ = rsa.newkeys(2048)
    class KeyResponse:
        status = 200
        data = json.dumps({"synthetic-key": public.save_pkcs1().decode()}).encode()
    def keys(self, *args, **kwargs):
        assert kwargs["timeout"] == 5
        return KeyResponse()
    monkeypatch.setattr(Request, "__call__", keys)
    token = google_jwt.encode(signer, claims).decode()
    if invalid:
        with pytest.raises(HTTPException) as error:
            google_auth.verify_google_credential(token)
        assert error.value.status_code == 401
    else:
        assert google_auth.verify_google_credential(token)["sub"] == "synthetic-subject"
