from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Company, Organization, OrganizationMemberRole, OrganizationMembership, OrgType, OrganizationStatus, SubscriptionTier, User
from app.models.f5_company_intelligence import F5CompanyProfile, F5PresenceType
from app.models.f5_company_intelligence import F5Classification, F5Freshness
from app.services.f5_company_intelligence import freshness_for_dates, normalize_company_name


@pytest.fixture()
def f5_context():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    users = [
        User(id=1, full_name="A User", email="f5-a@example.com", role="user", hashed_password="unused"),
        User(id=2, full_name="B User", email="f5-b@example.com", role="user", hashed_password="unused"),
    ]
    organizations = [
        Organization(public_id="f5-org-a", org_code="F5A", legal_name="F5 Organization A", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE),
        Organization(public_id="f5-org-b", org_code="F5B", legal_name="F5 Organization B", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE),
    ]
    db.add_all(users + organizations)
    db.flush()
    companies = [
        Company(organization_id=organizations[0].id, company_name="A Logistics", industry="Logistics", company_type="Private", headquarters_city="Kalaburagi", headquarters_state="Karnataka"),
        Company(organization_id=organizations[1].id, company_name="B Manufacturing", industry="Manufacturing", company_type="Private", headquarters_city="Pune", headquarters_state="Maharashtra"),
    ]
    db.add_all(companies)
    db.flush()
    db.add_all([
        OrganizationMembership(user_id=1, organization_id=organizations[0].id, role=OrganizationMemberRole.MANAGER),
        OrganizationMembership(user_id=2, organization_id=organizations[1].id, role=OrganizationMemberRole.MANAGER),
    ])
    db.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield db, organizations, companies
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def f5_client(email):
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer " + create_access_token({"sub": email})
    return client


def profile_payload(name="a logistics"):
    return {"normalized_name": name, "lifecycle_status": "ENRICHED", "duplicate_status": "NONE", "aliases": []}


def presence_payload():
    return {"presence_type": F5PresenceType.LOGISTICS_ACTIVITY.value, "region": "Kalaburagi", "classification": "FACT", "freshness": "FRESH", "confidence": 0.9}


def claim_payload(classification="FACT"):
    return {"claim": "Operates in Kalaburagi", "claim_type": "regional_presence", "classification": classification, "freshness": "FRESH", "confidence": 0.9, "confidence_reasons": ["Primary source"]}


def assessment_payload():
    return {"industry_classification": "FACT", "industry": "Logistics", "warehouse_suitability": "HIGH", "icp_classification": "RELEVANT", "dimensions": {"geography_fit": "HIGH"}, "reasons": ["Physical product movement"], "confidence": 0.87, "confidence_reasons": ["Recent regional evidence"], "freshness": "FRESH"}


def test_f5_company_name_normalization_is_conservative():
    assert normalize_company_name("Acme Logistics Pvt. Ltd.") == "acme logistics pvt ltd"
    assert normalize_company_name("ABC Private Limited") == "abc pvt ltd"
    assert normalize_company_name("ABC Holdings") != normalize_company_name("ABC Logistics")


def test_f5_freshness_is_deterministic_and_unknown_without_dates():
    now = datetime(2026, 1, 1)
    assert freshness_for_dates(None, now=now).value == "UNKNOWN"
    assert freshness_for_dates(datetime(2025, 10, 3), now=now).value == "FRESH"  # 90 days
    assert freshness_for_dates(datetime(2025, 10, 2), now=now).value == "AGING"  # 91 days
    assert freshness_for_dates(datetime(2025, 1, 1), now=now).value == "AGING"  # 365 days
    assert freshness_for_dates(datetime(2024, 12, 31), now=now).value == "STALE"  # 366 days
    assert freshness_for_dates(datetime(2025, 12, 1), now=now).value == "FRESH"
    assert freshness_for_dates(datetime(2025, 6, 1), now=now).value == "AGING"
    assert freshness_for_dates(datetime(2024, 1, 1), now=now).value == "STALE"


def test_f5_claim_contract_preserves_fact_inference_unknown():
    from app.schemas.f5_company_intelligence import F5ClaimWrite

    fact = F5ClaimWrite(claim="Operates in Kalaburagi", claim_type="regional_presence", classification=F5Classification.FACT, observed_at=datetime.utcnow(), freshness=F5Freshness.FRESH, confidence=0.96)
    inference = F5ClaimWrite(claim="May need additional capacity", claim_type="warehouse_suitability", classification=F5Classification.INFERENCE, confidence=0.78)
    unknown = F5ClaimWrite(claim="Current requirement is unknown", claim_type="requirement", classification=F5Classification.UNKNOWN)
    assert fact.classification is F5Classification.FACT
    assert inference.classification is F5Classification.INFERENCE
    assert unknown.classification is F5Classification.UNKNOWN


def test_f5_requirement_contract_is_unknown_by_default():
    from app.schemas.f5_company_intelligence import F5CompanyDetail

    assert F5CompanyDetail.model_fields["current_warehouse_requirement"].default == {"value": None, "classification": "UNKNOWN"}


def test_f5_api_requires_authentication_and_isolates_reads_and_mutations(f5_context):
    _, organizations, companies = f5_context
    anonymous = TestClient(app)
    assert anonymous.get(f"/f5/companies?organization_id={organizations[0].id}").status_code == 401

    a = f5_client("f5-a@example.com")
    b = f5_client("f5-b@example.com")
    assert a.get(f"/f5/companies?organization_id={organizations[0].id}").status_code == 200
    assert a.get(f"/f5/companies?organization_id={organizations[1].id}").status_code == 403
    assert b.get(f"/f5/companies/{companies[0].id}").status_code == 403
    assert a.put(f"/f5/companies/{companies[1].id}/profile", json=profile_payload("should not write")).status_code == 403
    assert a.get(f"/f5/companies/{companies[0].id}").status_code == 200


def test_f5_api_crud_validation_filters_and_pagination(f5_context):
    db, organizations, companies = f5_context
    a = f5_client("f5-a@example.com")
    company_id = companies[0].id

    assert a.put(f"/f5/companies/{company_id}/profile", json=profile_payload()).status_code == 200
    assert a.post(f"/f5/companies/{company_id}/regional-presence", json=presence_payload()).status_code == 201
    evidence = a.post(f"/f5/companies/{company_id}/evidence", json=claim_payload())
    assert evidence.status_code == 201
    assert evidence.json()["classification"] == "FACT"
    assessment = a.put(f"/f5/companies/{company_id}/icp", json=assessment_payload())
    assert assessment.status_code == 200
    assert assessment.json()["warehouse_suitability"] == "HIGH"

    assert a.get(f"/f5/companies?organization_id={organizations[0].id}&warehouse_suitability=HIGH").json()["total"] == 1
    assert a.get(f"/f5/companies?organization_id={organizations[0].id}&geography=Kalaburagi").json()["total"] == 1
    assert a.get(f"/f5/companies?organization_id={organizations[0].id}&freshness=STALE").json()["total"] == 0
    assert a.get(f"/f5/companies?organization_id={organizations[0].id}&page=1&page_size=1").json()["page_size"] == 1
    assert a.get(f"/f5/companies/{company_id}").json()["current_warehouse_requirement"] == {"value": None, "classification": "UNKNOWN"}
    assert a.post(f"/f5/companies/{company_id}/evidence", json={"claim": "", "claim_type": "x", "classification": "FACT"}).status_code == 422
    assert a.get("/f5/companies/999999").status_code == 404