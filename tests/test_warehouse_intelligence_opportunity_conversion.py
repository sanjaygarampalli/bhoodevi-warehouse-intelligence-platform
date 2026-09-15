from datetime import datetime

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Company, DealPipelineStage, Lead, Organization, OrganizationStatus, OrgType,
    Requirement, RequirementStatus, SubscriptionTier, User, Warehouse, WarehouseMatch,
    WarehouseMatchStatus, WarehouseType,
)
from app.models.warehouse import AvailabilityStatus
from app.models.warehouse_match import MatchedBy
from app.models.warehouse_intelligence_conversion import WarehouseIntelligenceConversionStatus
from app.schemas.warehouse_intelligence_conversion import WarehouseMatchOpportunityConversionRequest
from app.services.deal_workflow import DealConflict
from app.services.warehouse_intelligence_conversion import WarehouseIntelligenceOpportunityConversionService


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def flow(db):
    org = Organization(public_id="conversion-org", org_code="CONV", legal_name="Conversion Org", org_type=OrgType.PVT_LTD,
                       subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    user = User(full_name="Conversion User", email="conversion@example.com", hashed_password="unused", role="admin")
    db.add_all([org, user]); db.flush()
    company = Company(organization_id=org.id, company_name="Prospect", industry="Logistics", company_type="Private")
    db.add(company); db.flush()
    lead = Lead(lead_number="CONV-LEAD", company_id=company.id)
    db.add(lead); db.flush()
    requirement = Requirement(lead_id=lead.id, title="Space", requirement_status=RequirementStatus.ACTIVE)
    warehouse = Warehouse(organization_id=org.id, owner_id=user.id, warehouse_name="Warehouse", city="Pune", state="Maharashtra",
                          warehouse_type=WarehouseType.COVERED, availability_status=AvailabilityStatus.AVAILABLE)
    db.add_all([requirement, warehouse]); db.flush()
    match = WarehouseMatch(lead_id=lead.id, requirement_id=requirement.id, warehouse_id=warehouse.id, match_score=90,
                           status=WarehouseMatchStatus.LEAD_CHOSEN, matched_by=MatchedBy.MANUAL)
    stage = DealPipelineStage(organization_id=org.id, stage_name="Qualification", stage_key="QUALIFICATION", stage_order=0)
    db.add_all([match, stage]); db.commit()
    return {"org": org, "user": user, "lead": lead, "requirement": requirement, "warehouse": warehouse, "match": match, "stage": stage}


def payload(flow, **overrides):
    values = {"deal_name": "Converted opportunity", "requirement_id": flow["requirement"].id, "stage_id": flow["stage"].id}
    values.update(overrides)
    return WarehouseMatchOpportunityConversionRequest(**values)


def test_happy_path_persists_auditable_conversion_and_deal(db, flow):
    conversion, deal, created = WarehouseIntelligenceOpportunityConversionService().convert_warehouse_match(
        db, flow["match"].id, payload(flow), user_id=flow["user"].id, organization_id=flow["org"].id,
    )
    assert created is True
    assert conversion.status == WarehouseIntelligenceConversionStatus.CONVERTED
    assert conversion.converted_at is not None
    assert conversion.deal_id == deal.id
    assert deal.organization_id == flow["org"].id
    assert deal.lead_id == flow["lead"].id
    assert deal.requirement_id == flow["requirement"].id
    assert deal.selected_warehouse_match_id == flow["match"].id
    assert flow["match"].status == WarehouseMatchStatus.CONVERTED


def test_conversion_is_idempotent_and_creates_one_deal(db, flow):
    service = WarehouseIntelligenceOpportunityConversionService()
    first, deal, _ = service.convert_warehouse_match(db, flow["match"].id, payload(flow), user_id=flow["user"].id, organization_id=flow["org"].id)
    second, same_deal, created = service.convert_warehouse_match(db, flow["match"].id, payload(flow), user_id=flow["user"].id, organization_id=flow["org"].id)
    assert created is False
    assert second.id == first.id
    assert same_deal.id == deal.id
    from app.models import Deal
    assert db.scalar(select(DealPipelineStage.id).where(DealPipelineStage.id == flow["stage"].id))
    assert len(db.execute(select(Deal)).scalars().all()) == 1


def test_cross_organization_source_is_rejected(db, flow):
    other = Organization(public_id="other-org", org_code="OTHER", legal_name="Other Org", org_type=OrgType.PVT_LTD,
                         subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    db.add(other); db.commit()
    with pytest.raises(ValueError, match="organization"):
        WarehouseIntelligenceOpportunityConversionService().convert_warehouse_match(
            db, flow["match"].id, payload(flow), user_id=flow["user"].id, organization_id=other.id,
        )
    from app.models import Deal
    assert db.scalar(select(Deal.id)) is None


def test_requirement_mismatch_and_ineligible_match_create_no_deal(db, flow):
    wrong = Requirement(lead_id=flow["lead"].id, title="Wrong", requirement_status=RequirementStatus.ACTIVE)
    db.add(wrong); db.commit()
    service = WarehouseIntelligenceOpportunityConversionService()
    with pytest.raises(DealConflict, match="Requirement"):
        service.convert_warehouse_match(db, flow["match"].id, payload(flow, requirement_id=wrong.id), user_id=flow["user"].id, organization_id=flow["org"].id)
    flow["match"].status = WarehouseMatchStatus.REJECTED
    db.commit()
    with pytest.raises(ValueError, match="eligible"):
        service.convert_warehouse_match(db, flow["match"].id, payload(flow), user_id=flow["user"].id, organization_id=flow["org"].id)
    from app.models import Deal
    assert db.scalar(select(Deal.id)) is None


def test_deal_failure_rolls_back_conversion_and_deal(db, flow):
    service = WarehouseIntelligenceOpportunityConversionService()
    with pytest.raises(LookupError):
        service.convert_warehouse_match(db, flow["match"].id, payload(flow, stage_id=99999), user_id=flow["user"].id, organization_id=flow["org"].id)
    from app.models import Deal
    assert db.scalar(select(Deal.id)) is None
    assert service.repository.get_by_source(db, flow["match"].id) is None