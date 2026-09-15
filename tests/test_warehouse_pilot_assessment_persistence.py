from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Company, Organization, OrgType, OrganizationStatus, SubscriptionTier, User, Warehouse
from app.models.warehouse_pilot_assessment import WarehousePilotAssessment
from app.schemas.warehouse_pilot_assessment import WarehousePilotAssessmentCreateRequest
from app.services.warehouse_pilot_assessment_persistence import WarehousePilotAssessmentPersistenceService


def _fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    org = Organization(public_id="wpa-org", org_code="WPA", legal_name="WPA Org", org_type=OrgType.OTHER, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    other = Organization(public_id="wpa-other", org_code="WPO", legal_name="Other Org", org_type=OrgType.OTHER, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    user = User(full_name="Assessor", email="wpa-assessor@example.com", hashed_password="unused")
    db.add_all([org, other, user]); db.flush()
    company = Company(organization_id=org.id, company_name="Assessed Company", industry="Logistics", company_type="Private")
    warehouse = Warehouse(organization_id=org.id, owner_id=user.id, warehouse_name="Assessed Warehouse", city="Pune", state="Maharashtra")
    other_warehouse = Warehouse(organization_id=other.id, owner_id=user.id, warehouse_name="Other Warehouse", city="Pune", state="Maharashtra")
    db.add_all([company, warehouse, other_warehouse]); db.commit()
    return engine, db, org, other, user, company, warehouse, other_warehouse


def test_persistence_uses_existing_evaluator_and_allows_reassessment(monkeypatch):
    engine, db, org, _, user, company, warehouse, _ = _fixture()
    result = {"warehouse_id": warehouse.id, "company_id": company.id, "technical_score": 91, "technical_classification": "EXCELLENT", "mandatory_gaps": [], "planned_capabilities": [], "factor_results": [{"factor": "gate", "status": "SATISFIED"}], "commercial_fit": "CONFIRMED", "commercial_reasons": ["confirmed"], "availability_fit": "CONFIRMED", "availability_reasons": ["available"], "operational_readiness": "READY", "operational_reasons": ["ready"], "requirement_confidence": "CONFIRMED", "overall_classification": "STRONG_FIT", "explanation": ["good"]}
    evaluator = Mock(); evaluator.evaluate.return_value = result
    service = WarehousePilotAssessmentPersistenceService(); service.evaluator = evaluator
    payload = WarehousePilotAssessmentCreateRequest(warehouse_id=warehouse.id, company_id=company.id)
    first = service.assess_and_persist(db, payload, user_id=user.id, organization_id=org.id)
    result["overall_classification"] = "CONDITIONAL_FIT"
    second = service.assess_and_persist(db, payload, user_id=user.id, organization_id=org.id)
    assert first.id != second.id
    assert first.overall_classification == "STRONG_FIT"
    assert second.overall_classification == "CONDITIONAL_FIT"
    assert evaluator.evaluate.call_count == 2
    assert db.scalar(select(WarehousePilotAssessment).where(WarehousePilotAssessment.id == first.id)).assessed_by_user_id == user.id
    db.close(); engine.dispose()


def test_cross_organization_rejected_and_result_fields_are_not_requestable():
    engine, db, org, other, user, company, _, other_warehouse = _fixture()
    with pytest.raises(ValueError, match="organization"):
        WarehousePilotAssessmentPersistenceService().assess_and_persist(
            db, WarehousePilotAssessmentCreateRequest(warehouse_id=other_warehouse.id, company_id=company.id), user_id=user.id, organization_id=other.id,
        )
    with pytest.raises(ValueError):
        WarehousePilotAssessmentCreateRequest(warehouse_id=other_warehouse.id, company_id=company.id, overall_classification="STRONG_FIT")
    db.close(); engine.dispose()


def test_persistence_failure_rolls_back_assessment(monkeypatch):
    engine, db, org, _, user, company, warehouse, _ = _fixture()
    service = WarehousePilotAssessmentPersistenceService()
    service.evaluator.evaluate = Mock(return_value={"overall_classification": "WEAK_FIT", "warehouse_id": warehouse.id, "company_id": company.id})
    monkeypatch.setattr(service.repository, "create", Mock(side_effect=RuntimeError("write failed")))
    with pytest.raises(ValueError, match="persistence failed"):
        service.assess_and_persist(db, WarehousePilotAssessmentCreateRequest(warehouse_id=warehouse.id, company_id=company.id), user_id=user.id, organization_id=org.id)
    assert db.scalar(select(WarehousePilotAssessment)) is None
    db.close(); engine.dispose()