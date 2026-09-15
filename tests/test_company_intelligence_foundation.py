import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import (
    Company,
    Organization,
    OrganizationMemberRole,
    OrganizationMembership,
    OrgType,
    OrganizationStatus,
    SubscriptionTier,
    User,
)
from app.models.company_intelligence import (
    CompanyContact,
    CompanyContactMethod,
    CompanyIntelligenceProfile,
    CompanyWarehouseProfile,
    CompanyICPAssessment,
    CompanyOpportunityAssessment,
    CompanyNextBestAction,
    ContactDepartment,
    ContactMethodType,
    ContactSeniority,
    VerificationStatus,
)
from app.schemas.company_intelligence import ContactMethodUpdate, ContactMethodWrite, ContactWrite, IntelligenceProfileWrite, WarehouseProfileWrite
from app.services.company_intelligence import CompanyIntelligenceService, InvalidContactMethodValue


@pytest.fixture()
def isolated_company_api():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, autoflush=False)()
    org_a = Organization(public_id="org-a", org_code="ORGA", legal_name="Organization A", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    org_b = Organization(public_id="org-b", org_code="ORGB", legal_name="Organization B", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    user = User(full_name="Organization B User", email="org-b-user@example.com", role="user", hashed_password="unused")
    db.add_all([org_a, org_b, user])
    db.flush()
    db.add(OrganizationMembership(user_id=user.id, organization_id=org_b.id, role=OrganizationMemberRole.ADMIN))
    company = Company(organization_id=org_a.id, company_name="Organization A Company", industry="Logistics", company_type="PVT_LTD")
    db.add(company)
    db.flush()
    profile = CompanyIntelligenceProfile(organization_id=org_a.id, company_id=company.id, industry="Logistics")
    warehouse = CompanyWarehouseProfile(organization_id=org_a.id, company_id=company.id)
    contact = CompanyContact(organization_id=org_a.id, company_id=company.id, full_name="A Decision Maker", department=ContactDepartment.LOGISTICS, seniority=ContactSeniority.DIRECTOR)
    db.add_all([profile, warehouse, contact])
    db.flush()
    method = CompanyContactMethod(contact_id=contact.id, method_type=ContactMethodType.EMAIL, value="a@example.com", normalized_value="a@example.com")
    db.add(method)
    db.commit()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        client.headers["Authorization"] = "Bearer " + create_access_token({"sub": user.email})
        yield db, client, company, profile, warehouse, contact, method
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_profile_ranges_and_nonnegative_validation():
    with pytest.raises(ValidationError):
        IntelligenceProfileWrite(employee_count_min=10, employee_count_max=2)
    with pytest.raises(ValidationError):
        WarehouseProfileWrite(estimated_area_min_sqft=100, estimated_area_max_sqft=10)
    with pytest.raises(ValidationError):
        IntelligenceProfileWrite(employee_count_min=-1)


def test_contact_method_verification_claims_are_explicit():
    with pytest.raises(ValidationError):
        ContactMethodWrite(method_type=ContactMethodType.EMAIL, value="person@example.com", is_verified=True)
    with pytest.raises(ValidationError):
        ContactMethodWrite(method_type=ContactMethodType.EMAIL, value="not-an-email")
    verified = ContactMethodWrite(method_type=ContactMethodType.EMAIL, value="person@example.com", is_verified=True, verification_status=VerificationStatus.VERIFIED)
    assert verified.verification_status is VerificationStatus.VERIFIED


@pytest.mark.parametrize(
    ("method_type", "value", "valid"),
    [
        (ContactMethodType.EMAIL, "new.person@example.com", True),
        (ContactMethodType.EMAIL, "invalid-email", False),
        (ContactMethodType.LINKEDIN, "https://www.linkedin.com/in/person", True),
        (ContactMethodType.LINKEDIN, "https://example.com/person", False),
        (ContactMethodType.WEBSITE, "https://example.com", True),
        (ContactMethodType.WEBSITE, "example.com", False),
    ],
)
def test_contact_method_patch_is_validated_using_stored_type(method_type, value, valid):
    if valid:
        CompanyIntelligenceService._validate_method_value(value, method_type)
    else:
        with pytest.raises(InvalidContactMethodValue):
            CompanyIntelligenceService._validate_method_value(value, method_type)


def test_contact_method_patch_service_rejects_invalid_value_without_writing():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        organization = Organization(
            public_id="org-contact-test",
            org_code="CONTACTTEST",
            legal_name="Contact Test Organization",
            org_type=OrgType.PVT_LTD,
            subscription_tier=SubscriptionTier.FREE,
            status=OrganizationStatus.ACTIVE,
        )
        db.add(organization)
        db.flush()
        company = Company(
            organization_id=organization.id,
            company_name="Contact Test Company",
            industry="Logistics",
            company_type="PVT_LTD",
        )
        db.add(company)
        db.flush()
        contact = CompanyContact(
            organization_id=organization.id,
            company_id=company.id,
            full_name="Contact Test",
            department=ContactDepartment.OTHER,
            seniority=ContactSeniority.UNKNOWN,
        )
        db.add(contact)
        db.flush()
        method = CompanyContactMethod(
            contact_id=contact.id,
            method_type=ContactMethodType.EMAIL,
            value="person@example.com",
            normalized_value="person@example.com",
        )
        db.add(method)
        db.commit()
        with pytest.raises(InvalidContactMethodValue):
            CompanyIntelligenceService().update_method(
                db, method.id, organization.id, ContactMethodUpdate(value="not-an-email")
            )
        db.expire_all()
        stored = db.get(CompanyContactMethod, method.id)
        assert stored.value == "person@example.com"
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_verified_contact_method_cannot_be_silently_replaced_or_downgraded(isolated_company_api):
    db, _, company, _, _, _, method = isolated_company_api
    method.is_verified = True
    method.verification_status = VerificationStatus.VERIFIED
    db.commit()

    with pytest.raises(InvalidContactMethodValue):
        CompanyIntelligenceService().update_method(
            db, method.id, company.organization_id, ContactMethodUpdate(value="replacement@example.com")
        )
    with pytest.raises(InvalidContactMethodValue):
        CompanyIntelligenceService().update_method(
            db, method.id, company.organization_id, ContactMethodUpdate(is_verified=False)
        )

    db.expire_all()
    stored = db.get(CompanyContactMethod, method.id)
    assert stored.value == "a@example.com"
    assert stored.verification_status is VerificationStatus.VERIFIED


def test_verified_contact_method_allows_explicit_verified_correction(isolated_company_api):
    db, _, company, _, _, _, method = isolated_company_api
    method.is_verified = True
    method.verification_status = VerificationStatus.VERIFIED
    db.commit()

    updated = CompanyIntelligenceService().update_method(
        db,
        method.id,
        company.organization_id,
        ContactMethodUpdate(
            value="corrected@example.com",
            is_verified=True,
            verification_status=VerificationStatus.VERIFIED,
        ),
    )

    assert updated.value == "corrected@example.com"
    assert updated.verification_status is VerificationStatus.VERIFIED


def test_cross_organization_module_one_endpoints_reject_without_state_change(isolated_company_api):
    db, client, company, profile, warehouse, contact, method = isolated_company_api
    before = {
        "profile": profile.industry,
        "warehouse": warehouse.warehouse_requirement_notes,
        "contact": contact.full_name,
        "method": method.value,
    }
    attempts = [
        ("get", f"/companies/{company.id}/intelligence-profile", None),
        ("post", f"/companies/{company.id}/intelligence-profile", {}),
        ("patch", f"/companies/{company.id}/intelligence-profile", {"industry": "Changed"}),
        ("get", f"/companies/{company.id}/warehouse-profile", None),
        ("post", f"/companies/{company.id}/warehouse-profile", {}),
        ("patch", f"/companies/{company.id}/warehouse-profile", {"warehouse_requirement_notes": "Changed"}),
        ("get", f"/company-contacts/{contact.id}", None),
        ("patch", f"/company-contacts/{contact.id}", {"full_name": "Changed"}),
        ("get", f"/company-contact-methods/{method.id}", None),
        ("patch", f"/company-contact-methods/{method.id}", {"value": "changed@example.com"}),
        ("get", f"/companies/{company.id}/icp-assessment", None),
        ("post", f"/companies/{company.id}/icp-assessment/recalculate", None),
        ("get", f"/companies/{company.id}/opportunity-assessment", None),
        ("post", f"/companies/{company.id}/opportunity-assessment/recalculate", None),
        ("get", f"/companies/{company.id}/next-best-action", None),
        ("post", f"/companies/{company.id}/next-best-action/recalculate", None),
    ]
    for verb, path, payload in attempts:
        response = getattr(client, verb)(path, json=payload) if payload is not None else getattr(client, verb)(path)
        assert response.status_code in {403, 404}
    db.expire_all()
    assert db.get(CompanyIntelligenceProfile, profile.id).industry == before["profile"]
    assert db.get(CompanyWarehouseProfile, warehouse.id).warehouse_requirement_notes == before["warehouse"]
    assert db.get(CompanyContact, contact.id).full_name == before["contact"]
    assert db.get(CompanyContactMethod, method.id).value == before["method"]


def test_primary_switch_is_contact_scoped_and_leaves_other_contact_unchanged(isolated_company_api):
    db, _, _, _, _, contact, method = isolated_company_api
    other = CompanyContact(organization_id=contact.organization_id, company_id=contact.company_id, full_name="Other Contact", department=ContactDepartment.OTHER, seniority=ContactSeniority.UNKNOWN)
    db.add(other)
    db.flush()
    second = CompanyContactMethod(contact_id=contact.id, method_type=ContactMethodType.EMAIL, value="second@example.com", normalized_value="second@example.com")
    other_primary = CompanyContactMethod(contact_id=other.id, method_type=ContactMethodType.EMAIL, value="other@example.com", normalized_value="other@example.com", is_primary=True)
    db.add_all([second, other_primary])
    db.commit()
    CompanyIntelligenceService().update_method(db, second.id, contact.organization_id, ContactMethodUpdate(is_primary=True))
    assert db.scalar(select(CompanyContactMethod).where(CompanyContactMethod.contact_id == contact.id, CompanyContactMethod.is_primary.is_(True))).id == second.id
    assert db.get(CompanyContactMethod, other_primary.id).is_primary is True


def test_contact_quality_explanation_matches_deterministic_factors():
    contact = CompanyContact(
        organization_id=1,
        company_id=1,
        full_name="Warehouse Director",
        department=ContactDepartment.LOGISTICS,
        seniority=ContactSeniority.DIRECTOR,
        is_primary=True,
        methods=[],
    )
    score, explanation = CompanyIntelligenceService.contact_quality(contact)
    assert score == 80
    assert explanation["score"] == score
    assert "Relevant seniority" in explanation["reasons"]
    assert "Warehouse-related department" in explanation["reasons"]
    assert "Primary contact" in explanation["reasons"]


def test_contact_intelligence_filters_and_ranking_are_deterministic(isolated_company_api):
    db, client, company, *_ = isolated_company_api
    service = CompanyIntelligenceService()
    strong = CompanyContact(
        organization_id=company.organization_id,
        company_id=company.id,
        full_name="Supply Chain Director",
        job_title="Head of Supply Chain",
        department=ContactDepartment.SUPPLY_CHAIN,
        seniority=ContactSeniority.HEAD,
    )
    same_name = CompanyContact(
        organization_id=company.organization_id,
        company_id=company.id,
        full_name="Supply Chain Director",
        job_title="Analyst",
        department=ContactDepartment.OTHER,
        seniority=ContactSeniority.UNKNOWN,
    )
    db.add_all([strong, same_name])
    db.flush()
    db.add_all([
        CompanyContactMethod(
            contact_id=strong.id,
            method_type=ContactMethodType.EMAIL,
            value="Director@Example.com",
            normalized_value="director@example.com",
            verification_status=VerificationStatus.VERIFIED,
            is_verified=True,
        ),
        CompanyContactMethod(
            contact_id=strong.id,
            method_type=ContactMethodType.LINKEDIN,
            value="https://www.linkedin.com/in/director",
            normalized_value="https://www.linkedin.com/in/director",
        ),
    ])
    db.commit()

    first = service.contact_intelligence(db, company.id, company.organization_id)
    second = service.contact_intelligence(db, company.id, company.organization_id)
    assert [item["contact"].id for item in first["contacts"]] == [item["contact"].id for item in second["contacts"]]
    assert first["contacts"][0]["contact"].id == strong.id
    assert first["contacts"][0]["human_review_required"] is True
    assert first["contacts"][0]["reasons"]

    items, total = service.list_contacts(db, company.id, company.organization_id, 1, 25, search="Analyst")
    assert total == 1
    assert items[0].id == same_name.id
    items, total = service.list_contacts(db, company.id, company.organization_id, 1, 25, verification_status=VerificationStatus.VERIFIED)
    assert total == 1
    assert items[0].id == strong.id
    assert client.get(f"/companies/{company.id}/contact-intelligence").status_code == 403


def test_contact_identity_duplicates_are_rejected_but_same_names_are_allowed(isolated_company_api):
    db, _, _, _, _, contact, _ = isolated_company_api
    service = CompanyIntelligenceService()
    other = CompanyContact(
        organization_id=contact.organization_id,
        company_id=contact.company_id,
        full_name=contact.full_name,
        department=ContactDepartment.OTHER,
        seniority=ContactSeniority.UNKNOWN,
    )
    db.add(other)
    db.commit()
    with pytest.raises(Exception, match="Contact identity already exists"):
        service.add_method(db, other.id, contact.organization_id, ContactMethodWrite(method_type=ContactMethodType.EMAIL, value="A@EXAMPLE.COM"))
    assert other.id != contact.id