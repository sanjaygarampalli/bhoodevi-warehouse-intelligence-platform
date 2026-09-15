from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Company, MarketSignal, MarketSignalStatus, MarketSignalType, MarketSignalSourceType,
    MarketSignalConfidence, RequirementCandidate, RequirementCandidateStatus,
    DemandStrength, Organization, OrganizationStatus, OrgType, SubscriptionTier, User,
    Lead, Requirement, RequirementCandidateConversion, OrganizationMembership,
    OrganizationMemberRole, MembershipStatus,
)
from app.schemas.requirement_candidate_conversion import RequirementCandidateConversionRequest
from app.services.requirement_candidate_conversion import RequirementCandidateConversionService
import pytest


def test_candidate_conversion_is_explicit_idempotent_and_preserves_source():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org = Organization(public_id="rcc-org", org_code="RCC", legal_name="RCC", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
        user = User(full_name="RCC User", email="rcc@example.com", hashed_password="unused", role="admin")
        db.add_all([org, user]); db.flush()
        db.add(OrganizationMembership(
            user_id=user.id,
            organization_id=org.id,
            role=OrganizationMemberRole.MEMBER,
            status=MembershipStatus.ACTIVE,
        ))
        company = Company(organization_id=org.id, company_name="Prospect", industry="Logistics", company_type="Private")
        signal = MarketSignal(organization_id=org.id, title="Expansion", signal_type=MarketSignalType.LOGISTICS_EXPANSION, status=MarketSignalStatus.VERIFIED, source_type=MarketSignalSourceType.NEWS, confidence_level=MarketSignalConfidence.HIGH)
        db.add_all([company, signal]); db.flush()
        candidate = RequirementCandidate(organization_id=org.id, company_id=company.id, market_signal_id=signal.id, status=RequirementCandidateStatus.ACCEPTED, demand_strength=DemandStrength.STRONG, confidence_level=MarketSignalConfidence.HIGH, summary="Warehouse space needed", reasoning="Verified expansion", city="Pune", state="Maharashtra", country="India")
        db.add(candidate); db.commit()
        request = RequirementCandidateConversionRequest(lead_number="RCC-LEAD")
        service = RequirementCandidateConversionService()

        conversion, resolved_company, lead, requirement, created = service.convert(db, candidate.id, request, user_id=user.id, organization_id=org.id)
        again, _, same_lead, same_requirement, created_again = service.convert(db, candidate.id, request, user_id=user.id, organization_id=org.id)

        assert created is True
        assert created_again is False
        assert resolved_company.id == company.id
        assert lead.id == same_lead.id
        assert requirement.id == same_requirement.id
        assert candidate.status == RequirementCandidateStatus.CONVERTED
        assert conversion.requirement_candidate_id == candidate.id
        assert again.id == conversion.id
        assert db.scalar(select(Lead.id)) == lead.id
        assert db.scalar(select(Requirement.id)) == requirement.id
        assert db.scalar(select(RequirementCandidateConversion.id)) == conversion.id
    engine.dispose()


def _candidate_fixture(db, *, status=RequirementCandidateStatus.ACCEPTED):
    org = Organization(public_id="fixture-org", org_code="FIX", legal_name="Fixture", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    other = Organization(public_id="other-org", org_code="OTH", legal_name="Other", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    user = User(full_name="Fixture User", email="fixture@example.com", hashed_password="unused", role="admin")
    db.add_all([org, other, user]); db.flush()
    db.add(OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role=OrganizationMemberRole.MEMBER,
        status=MembershipStatus.ACTIVE,
    ))
    company = Company(organization_id=org.id, company_name="Fixture Prospect", industry="Logistics", company_type="Private")
    signal = MarketSignal(organization_id=org.id, title="Signal", signal_type=MarketSignalType.LOGISTICS_EXPANSION, status=MarketSignalStatus.VERIFIED, source_type=MarketSignalSourceType.NEWS, confidence_level=MarketSignalConfidence.HIGH)
    db.add_all([company, signal]); db.flush()
    candidate = RequirementCandidate(organization_id=org.id, company_id=company.id, market_signal_id=signal.id, status=status, demand_strength=DemandStrength.STRONG, confidence_level=MarketSignalConfidence.HIGH, summary="Space needed", reasoning="Evidence", city="Pune")
    db.add(candidate); db.commit()
    return org, other, user, candidate


def test_same_organization_active_write_member_can_own_converted_lead():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, _, user, candidate = _candidate_fixture(db)
        request = RequirementCandidateConversionRequest(lead_number="OWNER-1", owner_user_id=user.id)

        _, _, lead, _, created = RequirementCandidateConversionService().convert(
            db, candidate.id, request, user_id=user.id, organization_id=org.id,
        )

        assert created is True
        assert lead.owner_user_id == user.id
    engine.dispose()


@pytest.mark.parametrize(
    ("case", "expected_message"),
    [("nonexistent", "not found"), ("cross_org", "active organization membership"), ("inactive", "active organization membership"), ("viewer", "write access")],
)
def test_invalid_lead_owner_is_rejected_without_conversion(case, expected_message):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other, user, candidate = _candidate_fixture(db)
        if case == "nonexistent":
            owner_id = 999999
        elif case == "cross_org":
            owner = User(full_name="Other Owner", email="other-owner@example.com", hashed_password="unused", role="user")
            db.add(owner); db.flush()
            db.add(OrganizationMembership(user_id=owner.id, organization_id=other.id, role=OrganizationMemberRole.MEMBER, status=MembershipStatus.ACTIVE))
            db.commit()
            owner_id = owner.id
        else:
            owner = User(full_name=f"{case.title()} Owner", email=f"{case}@example.com", hashed_password="unused", role="user")
            db.add(owner); db.flush()
            db.add(OrganizationMembership(
                user_id=owner.id,
                organization_id=org.id,
                role=OrganizationMemberRole.VIEWER if case == "viewer" else OrganizationMemberRole.MEMBER,
                status=MembershipStatus.INACTIVE if case == "inactive" else MembershipStatus.ACTIVE,
            ))
            db.commit()
            owner_id = owner.id

        request = RequirementCandidateConversionRequest(lead_number=f"OWNER-{case}", owner_user_id=owner_id)
        with pytest.raises(ValueError, match=expected_message):
            RequirementCandidateConversionService().convert(
                db, candidate.id, request, user_id=user.id, organization_id=org.id,
            )
        assert db.scalar(select(Lead.id)) is None
        assert db.scalar(select(RequirementCandidateConversion.id)) is None
    engine.dispose()


def test_cross_organization_candidate_is_rejected_without_records():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, other, user, candidate = _candidate_fixture(db)
        with pytest.raises(ValueError, match="organization"):
            RequirementCandidateConversionService().convert(db, candidate.id, RequirementCandidateConversionRequest(lead_number="CROSS-1"), user_id=user.id, organization_id=other.id)
        assert db.scalar(select(Lead.id)) is None
        assert db.scalar(select(RequirementCandidateConversion.id)) is None
    engine.dispose()


def test_rejected_candidate_is_not_convertible():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, _, user, candidate = _candidate_fixture(db, status=RequirementCandidateStatus.REJECTED)
        with pytest.raises(ValueError, match="eligible"):
            RequirementCandidateConversionService().convert(db, candidate.id, RequirementCandidateConversionRequest(lead_number="REJECTED-1"), user_id=user.id, organization_id=org.id)
        assert db.scalar(select(Lead.id)) is None
    engine.dispose()


def test_downstream_failure_rolls_back_all_conversion_records(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        org, _, user, candidate = _candidate_fixture(db)
        service = RequirementCandidateConversionService()

        def fail(*args, **kwargs):
            raise RuntimeError("forced downstream failure")

        monkeypatch.setattr(service.requirements, "create_requirement_in_transaction", fail)
        with pytest.raises(ValueError, match="failed"):
            service.convert(db, candidate.id, RequirementCandidateConversionRequest(lead_number="ROLLBACK-1"), user_id=user.id, organization_id=org.id)
        assert db.scalar(select(Lead.id)) is None
        assert db.scalar(select(Requirement.id)) is None
        assert db.scalar(select(RequirementCandidateConversion.id)) is None
        assert db.get(RequirementCandidate, candidate.id).status == RequirementCandidateStatus.ACCEPTED
    engine.dispose()