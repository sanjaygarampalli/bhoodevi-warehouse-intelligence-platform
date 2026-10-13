"""Regression checks for auth, isolation and live evidence assessments."""
from datetime import datetime, timedelta, timezone

import pytest
import jwt
from pydantic import ValidationError
from sqlalchemy import select, func

from app.core.security import ALGORITHM, SECRET_KEY, decode_access_token, hash_password, verify_password, create_access_token
from app.models import Company, Lead, Warehouse, AvailabilityStatus, WarehouseMatch, DealPipelineStage
from app.models.requirement_intelligence import RequirementIntelligenceAssessment
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.deal import DealCreate
from app.services.deal import DealService
from app.services.deal_workflow import DealConflict
from tests.test_requirement_intelligence import requirement_context, requirement_client, evidence_payload


@pytest.mark.parametrize("password", ["a" * 73, "é" * 37, "abcde\x00fgh"])
def test_bcrypt_input_is_never_silently_truncated(password):
    with pytest.raises(ValidationError):
        UserCreate(full_name="Synthetic", email="synthetic@example.com", password=password)
    with pytest.raises(ValidationError):
        UserUpdate(password=password)
    with pytest.raises(ValueError):
        hash_password(password)
    assert not verify_password(password, hash_password("a" * 72))


def test_bcrypt_accepts_72_utf8_bytes_and_checks_password():
    password = "é" * 36
    hashed = hash_password(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


@pytest.mark.parametrize("payload", [
    {"sub": "synthetic@example.com"},
    {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
    {"sub": "", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
    {"sub": "synthetic@example.com", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
])
def test_tokens_require_subject_and_expiration(payload):
    assert decode_access_token(jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)) is None
    assert decode_access_token(create_access_token({"sub": "synthetic@example.com"}))["sub"] == "synthetic@example.com"
    assert decode_access_token("malformed") is None


def test_lead_cannot_be_moved_to_another_customer(requirement_context):
    db, _, requirements = requirement_context
    client = requirement_client("requirement-a@example.com")
    lead = db.get(Lead, requirements[0].lead_id)
    other = db.get(Lead, requirements[1].lead_id)
    original = lead.company_id
    response = client.put(f"/leads/{lead.id}", json={"company_id": other.company_id})
    assert response.status_code == 403
    db.refresh(lead)
    assert lead.company_id == original
    assert client.put(f"/leads/{lead.id}", json={"preferred_city": "Mysuru"}).status_code == 200


def test_organization_queries_do_not_expose_other_customers(requirement_context):
    _, organizations, _ = requirement_context
    client = requirement_client("requirement-a@example.com")
    assert [row["id"] for row in client.get("/organizations/").json()] == [organizations[0].id]
    assert client.get(f"/organizations/{organizations[1].id}").status_code == 403
    assert client.get(f"/organizations/code/{organizations[1].org_code}").status_code == 403
    assert client.get(f"/organizations/{organizations[0].id}").status_code == 200


def test_pipeline_stage_queries_enforce_organization_scope(requirement_context):
    db, organizations, _ = requirement_context
    stages = [DealPipelineStage(organization_id=org.id, stage_key="AUDIT", stage_name="Synthetic stage", stage_order=1) for org in organizations]
    db.add_all(stages); db.commit()
    client = requirement_client("requirement-a@example.com")
    assert client.get("/deal-pipeline-stages/").status_code == 400
    assert client.get(f"/deal-pipeline-stages/?organization_id={organizations[1].id}").status_code == 403
    assert client.get(f"/deal-pipeline-stages/{stages[1].id}").status_code == 403
    assert [row["id"] for row in client.get(f"/deal-pipeline-stages/?organization_id={organizations[0].id}").json()] == [stages[0].id]


def test_matching_excludes_other_organizations_and_rejects_relinking(requirement_context):
    db, organizations, requirements = requirement_context
    stock = [Warehouse(organization_id=org.id, owner_id=1, warehouse_name=f"Synthetic {org.id}",
                       city="Bengaluru", state="Karnataka",
                       availability_status=AvailabilityStatus.AVAILABLE) for org in organizations]
    db.add_all(stock)
    db.commit()
    client = requirement_client("requirement-a@example.com")
    req = requirements[0]
    path = f"/warehouse-matches/requirements/{req.id}"
    recommendations = client.get(path + "/recommendations")
    assert recommendations.status_code == 200
    assert [row["warehouse_id"] for row in recommendations.json()["matches"]] == [stock[0].id]
    assert client.post(path + "/generate").status_code == 200
    matches = client.get(f"/warehouse-matches/?requirement_id={req.id}").json()
    assert [row["warehouse_id"] for row in matches] == [stock[0].id]
    assert client.post("/warehouse-matches/", json={"lead_id": req.lead_id, "warehouse_id": stock[1].id,
                                                  "status": "AI_RECOMMENDED", "matched_by": "MANUAL", "match_score": 20}).status_code == 403
    assert client.put(f"/warehouse-matches/{matches[0]['id']}", json={"warehouse_id": stock[1].id}).status_code == 403
    assert client.put(f"/warehouse-matches/{matches[0]['id']}", json={"lead_id": requirements[1].lead_id}).status_code == 403
    assert client.get(f"/warehouse-matches/?requirement_id={req.id}&limit=-1").status_code == 422


def test_assessment_get_is_read_only_and_field_presence_is_not_confidence(requirement_context):
    db, _, requirements = requirement_context
    viewer = requirement_client("requirement-viewer@example.com")
    path = f"/requirement-intelligence/{requirements[0].id}/assessment"
    for _ in range(2):
        response = viewer.get(path)
        assert response.status_code == 200
        assert response.json()["id"] is None
        assert response.json()["requirement_confidence"] is None
        assert response.json()["geography_confidence"] is None
    assert db.scalar(select(func.count()).select_from(RequirementIntelligenceAssessment)) == 0


def test_deal_rejects_legacy_cross_customer_warehouse_match(requirement_context):
    db, organizations, requirements = requirement_context
    req = requirements[0]
    stock = Warehouse(organization_id=organizations[1].id, owner_id=1,
                      warehouse_name="Synthetic legacy stock", city="Bengaluru", state="Karnataka",
                      availability_status=AvailabilityStatus.AVAILABLE)
    stage = DealPipelineStage(organization_id=organizations[0].id, stage_key="AUDIT",
                              stage_name="Synthetic stage", stage_order=1)
    db.add_all([stock, stage]); db.commit()
    match = WarehouseMatch(lead_id=req.lead_id, requirement_id=req.id, warehouse_id=stock.id,
                           status="AI_RECOMMENDED", matched_by="MANUAL", match_score=20)
    db.add(match); db.commit()
    payload = DealCreate(deal_name="Synthetic lease", lead_id=req.lead_id, requirement_id=req.id,
                         stage_id=stage.id, selected_warehouse_match_id=match.id)
    with pytest.raises(DealConflict, match="Warehouse must belong"):
        DealService().create_deal(db, payload)
    stock.organization_id = organizations[0].id
    db.commit()
    assert DealService().create_deal(db, payload).organization_id == organizations[0].id


def test_verified_evidence_cannot_be_demoted_and_rewritten(requirement_context):
    _, _, requirements = requirement_context
    client = requirement_client("requirement-a@example.com")
    path = f"/requirement-intelligence/{requirements[0].id}/evidence"
    assert client.post(path, json=evidence_payload(evidence_date=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat())).status_code == 422
    record = client.post(path, json=evidence_payload()).json()
    item = f"{path}/{record['id']}"
    assert client.patch(item, json={"verification_status": "REVIEWED"}).status_code == 200
    verified = client.patch(item, json={"verification_status": "VERIFIED"}).json()
    assert client.patch(item, json={"verification_status": "UNVERIFIED"}).status_code == 409
    rejected = client.patch(item, json={"verification_status": "REJECTED"}).json()
    assert rejected["verified_at"] == verified["verified_at"]
    assert client.patch(item, json={"observed_evidence": "Replacement assertion"}).status_code == 409
