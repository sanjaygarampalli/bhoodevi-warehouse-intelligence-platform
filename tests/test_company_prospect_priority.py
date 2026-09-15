from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    Company,
    EvidenceCredibility,
    MarketSignal,
    MarketSignalEvidence,
    MarketSignalSourceType,
    MarketSignalStatus,
    MarketSignalType,
    Organization,
    OrganizationStatus,
    OrgType,
    SubscriptionTier,
)
from app.services.company_prospect_priority import CompanyProspectPriorityService


def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, autoflush=False)()


def organization(db, code):
    item = Organization(public_id=code, org_code=code, legal_name=code, org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    db.add(item)
    db.flush()
    return item


def company(db, org, name):
    item = Company(organization_id=org.id, company_name=name, industry="Manufacturing", company_type="Private")
    db.add(item)
    db.flush()
    return item


def signal(db, org, comp, status, signal_type=MarketSignalType.MANUFACTURING_EXPANSION):
    item = MarketSignal(organization_id=org.id, company_id=comp.id, title="Expansion", signal_type=signal_type, status=status, source_type=MarketSignalSourceType.COMPANY_ANNOUNCEMENT)
    db.add(item)
    db.flush()
    return item


def test_verified_relevant_signal_and_primary_evidence_are_explainable():
    engine, db = session()
    org = organization(db, "A")
    comp = company(db, org, "Expansion Co")
    item = signal(db, org, comp, MarketSignalStatus.VERIFIED, MarketSignalType.NEW_WAREHOUSE)
    db.add(MarketSignalEvidence(market_signal_id=item.id, evidence_type=MarketSignalSourceType.COMPANY_ANNOUNCEMENT, title="Official announcement", credibility_level=EvidenceCredibility.PRIMARY))
    db.commit()

    result = CompanyProspectPriorityService().assess(db, comp.id)
    assert result.priority_score >= 50
    assert result.priority.value in {"HIGH", "CRITICAL"}
    assert any("verified" in fact.lower() for fact in result.observed_facts)
    assert result.demand_strength == "STRONG"
    assert result.evidence_confidence == "HIGH"
    assert result.human_review_required is True
    assert "confirmed requirement" in result.inference
    db.close(); engine.dispose()


def test_low_information_and_rejected_signal_do_not_claim_demand():
    engine, db = session()
    org = organization(db, "A")
    empty = company(db, org, "Unknown Co")
    rejected = company(db, org, "Rejected Co")
    signal(db, org, rejected, MarketSignalStatus.REJECTED, MarketSignalType.NEW_WAREHOUSE)
    db.commit()

    service = CompanyProspectPriorityService()
    empty_result = service.assess(db, empty.id)
    rejected_result = service.assess(db, rejected.id)
    assert empty_result.priority_score <= 10
    assert empty_result.demand_strength == "NONE"
    assert empty_result.uncertainties
    assert rejected_result.priority_score <= 10
    assert rejected_result.demand_strength == "NONE"
    db.close(); engine.dispose()


def test_list_is_organization_scoped_and_deterministically_ranked():
    engine, db = session()
    org_a = organization(db, "A")
    org_b = organization(db, "B")
    high = company(db, org_a, "High")
    low = company(db, org_a, "Low")
    foreign = company(db, org_b, "Foreign")
    signal(db, org_a, high, MarketSignalStatus.VERIFIED, MarketSignalType.NEW_DISTRIBUTION_CENTER)
    signal(db, org_b, foreign, MarketSignalStatus.VERIFIED, MarketSignalType.NEW_WAREHOUSE)
    db.commit()

    result = CompanyProspectPriorityService().list(db, org_a.id)
    assert [item.company_name for item in result.items] == ["High", "Low"]
    assert all(item.organization_id == org_a.id for item in result.items)
    assert "Foreign" not in {item.company_name for item in result.items}
    assert CompanyProspectPriorityService().assess(db, foreign.id).organization_id == org_b.id
    db.close(); engine.dispose()