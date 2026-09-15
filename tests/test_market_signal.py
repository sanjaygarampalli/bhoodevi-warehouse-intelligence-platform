"""Market signal, evidence, assessment, and candidate workflow tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    Company,
    MarketSignal,
    MarketSignalStatus,
    RequirementCandidate,
    RequirementCandidateStatus,
    Organization,
    OrganizationMemberRole,
    OrganizationMembership,
    MembershipStatus,
    OrgType,
    OrganizationStatus,
    SubscriptionTier,
    User,
)


@pytest.fixture()
def market_context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    admin = User(id=1, full_name="Global Admin", email="signal-global@example.com", role="admin", hashed_password="unused")
    manager = User(id=2, full_name="Manager", email="signal-manager@example.com", role="user", hashed_password="unused")
    viewer = User(id=3, full_name="Viewer", email="signal-viewer@example.com", role="user", hashed_password="unused")
    outsider = User(id=4, full_name="Outsider", email="signal-outsider@example.com", role="user", hashed_password="unused")
    org_one = Organization(public_id="signal-org-1", org_code="SIG1", legal_name="Signal One", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    org_two = Organization(public_id="signal-org-2", org_code="SIG2", legal_name="Signal Two", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    db.add_all([admin, manager, viewer, outsider, org_one, org_two])
    db.flush()
    company = Company(organization_id=org_one.id, company_name="Acme Logistics", industry="Logistics", company_type="Private")
    db.add(company)
    db.flush()
    db.add_all([
        OrganizationMembership(user_id=2, organization_id=org_one.id, role=OrganizationMemberRole.MANAGER),
        OrganizationMembership(user_id=3, organization_id=org_one.id, role=OrganizationMemberRole.VIEWER),
        OrganizationMembership(user_id=4, organization_id=org_two.id, role=OrganizationMemberRole.MEMBER),
    ])
    db.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield db, org_one, org_two, company
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def client(email):
    http = TestClient(app)
    http.headers["Authorization"] = "Bearer " + create_access_token({"sub": email})
    return http


def signal_payload(org_id, company_id=None, signal_type="NEW_WAREHOUSE", status=None, confidence="HIGH"):
    payload = {
        "organization_id": org_id,
        "company_id": company_id,
        "title": "New warehouse announcement",
        "description": "A new logistics facility was announced.",
        "signal_type": signal_type,
        "source_type": "COMPANY_ANNOUNCEMENT",
        "source_name": "Acme announcement",
        "source_url": "https://example.com/source",
        "city": "Bengaluru",
        "state": "Karnataka",
        "country": "India",
        "confidence_level": confidence,
    }
    if status is not None:
        payload["status"] = status
    return payload


def test_market_signal_authentication_and_organization_isolation(market_context):
    _, org_one, org_two, company = market_context
    assert TestClient(app).get(f"/market-signals?organization_id={org_one.id}").status_code == 401
    manager = client("signal-manager@example.com")
    created = manager.post("/market-signals", json=signal_payload(org_one.id, company.id))
    assert created.status_code == 201
    assert manager.get(f"/market-signals?organization_id={org_two.id}").status_code == 403
    viewer = client("signal-viewer@example.com")
    assert viewer.get(f"/market-signals?organization_id={org_one.id}").status_code == 200
    assert viewer.post("/market-signals", json=signal_payload(org_one.id, company.id)).status_code == 403


def test_unlinked_signal_can_be_created_and_later_linked(market_context):
    _, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    created = http.post("/market-signals", json=signal_payload(org_one.id))
    assert created.status_code == 201
    signal_id = created.json()["id"]
    updated = http.patch(f"/market-signals/{signal_id}", json={"company_id": company.id})
    assert updated.status_code == 200
    assert updated.json()["company_id"] == company.id


def test_viewer_cannot_mutate_signal_evidence_lifecycle_or_candidate(market_context):
    _, org_one, _, company = market_context
    manager = client("signal-manager@example.com")
    viewer = client("signal-viewer@example.com")
    signal_id = manager.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]

    assert viewer.patch(f"/market-signals/{signal_id}", json={"title": "Changed"}).status_code == 403
    assert viewer.post(f"/market-signals/{signal_id}/evidence", json={
        "evidence_type": "NEWS", "title": "News", "credibility_level": "HIGH",
    }).status_code == 403
    assert viewer.post(f"/market-signals/{signal_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 403
    assert viewer.post(f"/market-signals/{signal_id}/requirement-candidate").status_code == 403


def test_inactive_member_cannot_read_or_write_market_signals(market_context):
    db, org_one, _, company = market_context
    db.query(OrganizationMembership).filter_by(user_id=3, organization_id=org_one.id).update({"status": MembershipStatus.INACTIVE})
    db.commit()
    viewer = client("signal-viewer@example.com")

    assert viewer.get(f"/market-signals?organization_id={org_one.id}").status_code == 403
    assert viewer.post("/market-signals", json=signal_payload(org_one.id, company.id)).status_code == 403


def test_foreign_company_is_rejected_on_signal_create_and_update(market_context):
    db, org_one, org_two, company = market_context
    foreign_company = Company(organization_id=org_two.id, company_name="Foreign Logistics", industry="Logistics", company_type="Private")
    db.add(foreign_company)
    db.commit()
    manager = client("signal-manager@example.com")

    assert manager.post("/market-signals", json=signal_payload(org_one.id, foreign_company.id)).status_code == 400
    signal_id = manager.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]
    assert manager.patch(f"/market-signals/{signal_id}", json={"company_id": foreign_company.id}).status_code == 400


def test_evidence_is_owned_through_parent_signal(market_context):
    _, org_one, _, company = market_context
    manager = client("signal-manager@example.com")
    outsider = client("signal-outsider@example.com")
    signal_id = manager.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]
    evidence = manager.post(f"/market-signals/{signal_id}/evidence", json={
        "evidence_type": "NEWS", "title": "Evidence", "credibility_level": "HIGH",
    })
    evidence_id = evidence.json()["id"]

    assert outsider.get(f"/market-signals/{signal_id}/evidence/{evidence_id}").status_code == 403
    assert outsider.patch(f"/market-signals/{signal_id}/evidence/{evidence_id}", json={"title": "Changed"}).status_code == 403


def test_assessment_separates_observation_inference_recommendation_and_confidence(market_context):
    _, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    signal_id = http.post("/market-signals", json=signal_payload(org_one.id, company.id, confidence="HIGH")).json()["id"]
    http.post(f"/market-signals/{signal_id}/evidence", json={
        "evidence_type": "COMPANY_ANNOUNCEMENT", "title": "Plant announcement", "excerpt": "Plant announced.", "credibility_level": "PRIMARY",
    })
    assessment = http.get(f"/market-signals/{signal_id}/assessment").json()

    assert assessment["observed_evidence"] == ["Plant announcement"]
    assert assessment["inference"]
    assert assessment["recommendation"] == assessment["recommended_next_step"]
    assert assessment["confidence_level"] == "HIGH"
    assert assessment["demand_strength"] == "STRONG"
    assert assessment["inference"] != assessment["recommendation"]


@pytest.mark.parametrize(("signal_type", "strength"), [
    ("NEW_WAREHOUSE", "STRONG"),
    ("NEW_DISTRIBUTION_CENTER", "STRONG"),
    ("LOGISTICS_EXPANSION", "STRONG"),
    ("COMPANY_EXPANSION", "MODERATE"),
    ("MANUFACTURING_EXPANSION", "POSSIBLE"),
])
def test_assessment_is_deterministic_and_conservative(market_context, signal_type, strength):
    _, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    signal_id = http.post("/market-signals", json=signal_payload(org_one.id, company.id, signal_type)).json()["id"]
    first = http.get(f"/market-signals/{signal_id}/assessment").json()
    second = http.get(f"/market-signals/{signal_id}/assessment").json()
    assert first == second
    assert first["demand_strength"] == strength
    assert first["indicates_potential_warehouse_demand"] is True
    assert signal_type in first["explanation"]


def test_evidence_and_verified_candidate_workflow(market_context):
    _, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    signal_id = http.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]
    evidence = http.post(f"/market-signals/{signal_id}/evidence", json={
        "evidence_type": "COMPANY_ANNOUNCEMENT",
        "source_name": "Official source",
        "title": "Facility announcement",
        "excerpt": "The company announced a new warehouse.",
        "credibility_level": "PRIMARY",
    })
    assert evidence.status_code == 201
    assert len(http.get(f"/market-signals/{signal_id}/evidence").json()) == 1
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 200
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "VERIFIED"}).status_code == 200
    candidate = http.post(f"/market-signals/{signal_id}/requirement-candidate")
    assert candidate.status_code == 201
    assert candidate.json()["market_signal_id"] == signal_id
    assert http.post(f"/market-signals/{signal_id}/requirement-candidate").status_code == 409
    assert http.get(f"/requirement-candidates?organization_id={org_one.id}").status_code == 200


def test_rejected_and_unlinked_signals_cannot_create_candidates(market_context):
    _, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    rejected_id = http.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]
    assert http.post(f"/market-signals/{rejected_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 200
    assert http.post(f"/market-signals/{rejected_id}/transition", json={"target_status": "REJECTED"}).status_code == 200
    rejected_assessment = http.get(f"/market-signals/{rejected_id}/assessment").json()
    assert rejected_assessment["indicates_potential_warehouse_demand"] is False
    assert http.post(f"/market-signals/{rejected_id}/requirement-candidate").status_code == 400
    unlinked_id = http.post("/market-signals", json=signal_payload(org_one.id)).json()["id"]
    assert http.post(f"/market-signals/{unlinked_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 200
    assert http.post(f"/market-signals/{unlinked_id}/transition", json={"target_status": "VERIFIED"}).status_code == 200
    assert http.post(f"/market-signals/{unlinked_id}/requirement-candidate").status_code == 400


def test_global_admin_access_and_openapi_registration(market_context):
    _, org_one, org_two, _ = market_context
    admin = client("signal-global@example.com")
    assert admin.get(f"/market-signals?organization_id={org_two.id}").status_code == 200
    paths = app.openapi()["paths"]
    assert "/market-signals" in paths
    assert "/market-signals/{signal_id}/evidence" in paths
    assert "/market-signals/{signal_id}/assessment" in paths
    assert "/market-signals/{signal_id}/transition" in paths
    assert "/requirement-candidates" in paths


def test_signal_lifecycle_rejects_patch_and_invalid_reversals(market_context):
    db, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    signal_id = http.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]

    assert http.patch(f"/market-signals/{signal_id}", json={"status": "UNDER_REVIEW"}).status_code == 422
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.DETECTED
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "VERIFIED"}).status_code == 400
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.DETECTED
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 200
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.UNDER_REVIEW
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "VERIFIED", "review_notes": "Primary source reviewed by manager."}).status_code == 200
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.VERIFIED
    reviewed = db.get(MarketSignal, signal_id)
    assert reviewed.reviewed_by_user_id == 2
    assert reviewed.reviewed_at is not None
    assert reviewed.review_notes == "Primary source reviewed by manager."
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 400
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.VERIFIED
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "ARCHIVED"}).status_code == 200
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.ARCHIVED
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "VERIFIED"}).status_code == 400
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.ARCHIVED


def test_candidate_lifecycle_rejects_converted_and_invalid_transitions(market_context):
    _, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    signal_id = http.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]
    assert http.post(f"/market-signals/{signal_id}/evidence", json={
        "evidence_type": "COMPANY_ANNOUNCEMENT",
        "title": "Facility announcement",
        "credibility_level": "PRIMARY",
    }).status_code == 201
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 200
    assert http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "VERIFIED"}).status_code == 200
    candidate = http.post(f"/market-signals/{signal_id}/requirement-candidate")
    assert candidate.status_code == 201
    candidate_id = candidate.json()["id"]

    assert http.patch(f"/requirement-candidates/{candidate_id}", json={"status": "UNDER_REVIEW"}).status_code == 422
    assert http.post(f"/requirement-candidates/{candidate_id}/transition", json={"target_status": "CONVERTED"}).status_code == 400
    assert http.post(f"/requirement-candidates/{candidate_id}/transition", json={"target_status": "ACCEPTED"}).status_code == 400
    assert http.post(f"/requirement-candidates/{candidate_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 200
    assert http.post(f"/requirement-candidates/{candidate_id}/transition", json={"target_status": "ACCEPTED"}).status_code == 200
    assert http.post(f"/requirement-candidates/{candidate_id}/transition", json={"target_status": "REJECTED"}).status_code == 400


def test_transition_organization_isolation(market_context):
    db, org_one, _, company = market_context
    manager = client("signal-manager@example.com")
    outsider = client("signal-outsider@example.com")
    signal_id = manager.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]
    assert outsider.post(f"/market-signals/{signal_id}/transition", json={"target_status": "UNDER_REVIEW"}).status_code == 403
    assert db.scalar(select(MarketSignal.status).where(MarketSignal.id == signal_id)) == MarketSignalStatus.DETECTED


def test_candidate_integrity_error_is_translated_and_rolled_back(market_context, monkeypatch):
    db, org_one, _, company = market_context
    http = client("signal-manager@example.com")
    signal_id = http.post("/market-signals", json=signal_payload(org_one.id, company.id)).json()["id"]
    http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "UNDER_REVIEW"})
    http.post(f"/market-signals/{signal_id}/transition", json={"target_status": "VERIFIED"})

    original_commit = db.commit
    calls = {"count": 0}

    def fail_candidate_commit():
        calls["count"] += 1
        if calls["count"] == 1:
            raise IntegrityError("insert", {}, Exception("uq_requirement_candidates__market_signal"))
        original_commit()

    monkeypatch.setattr(db, "commit", fail_candidate_commit)
    response = http.post(f"/market-signals/{signal_id}/requirement-candidate")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    assert db.in_transaction() is False