from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Company, Organization, OrgType, OrganizationStatus, SubscriptionTier, User, Warehouse
from app.models.warehouse_capability import CapabilityStatus
from app.schemas.warehouse_capability import CapabilityProfileWrite
from app.schemas.warehouse_requirement import RequirementProfileWrite
from app.services.warehouse_capability_matching import evaluate_capability_match


def test_profile_validation_rejects_negative_and_invalid_ranges():
    with pytest.raises(ValueError):
        CapabilityProfileWrite(capabilities={"gate_width_ft": {"value": -1, "status": "CONFIRMED"}})
    with pytest.raises(ValueError):
        RequirementProfileWrite(requirements={
            "required_area_min_sqft": {"value": 5000, "priority": "MANDATORY"},
            "required_area_max_sqft": {"value": 1000, "priority": "MANDATORY"},
        })
    with pytest.raises(ValueError):
        RequirementProfileWrite(requirements={"container_access": {"value": True, "priority": "REQUIRED"}})


def test_confirmed_capability_satisfies_and_priorities_are_transparent():
    result = evaluate_capability_match(
        {"gate_width_ft": {"value": 40, "status": "CONFIRMED"}, "container_access": {"value": True, "status": "CONFIRMED"}},
        {"gate_width_ft": {"value": 35, "priority": "IMPORTANT"}, "container_access": {"value": True, "priority": "MANDATORY"}},
        1, 2,
    )
    assert result["mandatory_gap"] is False
    assert result["current_match_score"] == 100
    assert {factor["status"] for factor in result["factor_results"]} == {"SATISFIED"}


@pytest.mark.parametrize("status, expected", [("NOT_AVAILABLE", "NOT_AVAILABLE"), ("UNKNOWN", "UNKNOWN"), ("PLANNED", "PLANNED_IMPROVEMENT")])
def test_truth_status_never_becomes_current_satisfaction(status, expected):
    result = evaluate_capability_match(
        {"container_access": {"value": True, "status": status}},
        {"container_access": {"value": True, "priority": "MANDATORY"}}, 1, 2,
    )
    assert result["mandatory_gap"] is True
    assert result["classification"] == "NOT_SUITABLE"
    assert result["factor_results"][0]["status"] == expected
    if status == "PLANNED":
        assert result["planned_capabilities"] == ["container_access"]


def test_preferred_has_lower_weight_and_partial_classification():
    result = evaluate_capability_match(
        {"security_required": {"value": True, "status": "CONFIRMED"}},
        {"security_required": {"value": True, "priority": "PREFERRED"}, "water_required": {"value": True, "priority": "PREFERRED"}},
        1, 2,
    )
    assert result["current_match_score"] == 50
    assert result["classification"] == "PARTIAL"


def test_tenant_records_are_distinct_and_required_for_new_workflow():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = Organization(public_id="org", org_code="ORG", legal_name="Org", org_type=OrgType.OTHER,
                           subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
        db.add(org); db.flush()
        company = Company(organization_id=org.id, company_name="Company", industry="Logistics", company_type="Private")
        user = User(full_name="Owner", email="owner-module2@example.com", hashed_password="unused")
        db.add_all([company, user]); db.flush()
        warehouse = Warehouse(organization_id=org.id, owner_id=user.id, warehouse_name="Warehouse", city="Bengaluru", state="Karnataka")
        db.add(warehouse); db.commit()
        assert warehouse.organization_id == company.organization_id
    Base.metadata.drop_all(engine)