from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Company, Organization, OrganizationMembership, User
from app.models.company_intelligence import CompanyContact, CompanyContactMethod, ContactDepartment, ContactMethodType, ContactSeniority, VerificationStatus
from app.models.contact_workflow import ContactOutreachActivity, ContactOutreachMethod, OutreachOutcome
from app.models.organization import OrgType, OrganizationStatus, SubscriptionTier
from app.schemas.company import CompanyCreate
from app.schemas.response_qualification import ContactResolutionRequest, QualificationWrite
from app.services.response_qualification import ResponseQualificationService


@pytest.fixture()
def qualification_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    org = Organization(public_id="qualification-org", org_code="QUAL", legal_name="Qualification Org", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    user = User(full_name="Reviewer", email="reviewer@example.com", role="user", hashed_password="unused")
    db.add_all([org, user])
    db.flush()
    db.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role="MEMBER"))
    db.commit()
    yield db, org, user
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def make_company(db, org, name, website=None):
    company = Company(organization_id=org.id, company_name=name, industry="Logistics", company_type="PVT_LTD", website=website)
    db.add(company)
    db.flush()
    return company


def test_company_resolution_is_exact_or_ambiguous_without_auto_merge(qualification_db):
    db, org, _ = qualification_db
    service = ResponseQualificationService()
    company = make_company(db, org, "ABC Logistics Pvt Ltd", "https://abc.example.com")
    exact = service.resolve_company(db, org.id, " abc logistics pvt ltd ", "abc.example.com")
    assert exact["result"] == "EXACT_MATCH"
    assert exact["company_id"] == company.id
    make_company(db, org, "ABC Logistics India")
    ambiguous = service.resolve_company(db, org.id, "ABC Logistics", None)
    assert ambiguous["result"] == "POSSIBLE_MATCH"
    assert ambiguous["human_review_required"] is True


def test_contact_consolidation_reuses_company_and_preserves_verified_method(qualification_db):
    db, org, _ = qualification_db
    service = ResponseQualificationService()
    company = make_company(db, org, "Contact Company")
    contact = CompanyContact(organization_id=org.id, company_id=company.id, full_name="Priya Sharma", department=ContactDepartment.SUPPLY_CHAIN, seniority=ContactSeniority.HEAD)
    db.add(contact)
    db.flush()
    db.add(CompanyContactMethod(contact_id=contact.id, method_type=ContactMethodType.EMAIL, value="verified@example.com", normalized_value="verified@example.com", verification_status=VerificationStatus.VERIFIED, is_verified=True))
    db.commit()
    result = service.consolidate_contact(db, company.id, ContactResolutionRequest(full_name="Priya Sharma", email="verified@example.com", job_title="VP Supply Chain"))
    assert result["result"] == "EXACT_MATCH"
    assert db.query(Company).count() == 1
    assert db.get(CompanyContact, contact.id).job_title == "VP Supply Chain"
    assert db.query(CompanyContactMethod).filter_by(normalized_value="verified@example.com").one().verification_status == VerificationStatus.VERIFIED


def test_qualification_is_human_controlled_and_context_does_not_create_pipeline(qualification_db):
    db, org, user = qualification_db
    service = ResponseQualificationService()
    company = make_company(db, org, "Qualification Company")
    contact = CompanyContact(organization_id=org.id, company_id=company.id, full_name="Ravi Kumar", department=ContactDepartment.OPERATIONS, seniority=ContactSeniority.MANAGER)
    db.add(contact)
    db.flush()
    outreach = ContactOutreachActivity(organization_id=org.id, company_id=company.id, contact_id=contact.id, performed_by_user_id=user.id, method=ContactOutreachMethod.EMAIL, performed_at=datetime(2026, 9, 14), outcome=OutreachOutcome.INTERESTED)
    db.add(outreach)
    db.commit()
    assessment = service.qualification(db, company.id, contact.id, outreach.id, user.id, QualificationWrite(commercial_inference="Potential demand, not confirmed.", uncertainty=["Warehouse size unknown"]))
    assert assessment.human_review_required is True
    assert service.commercial_context(db, company.id)["context"] == "QUALIFICATION_IN_PROGRESS"
    assert not db.query(__import__("app.models.lead", fromlist=["Lead"]).Lead).filter_by(company_id=company.id).count()


def test_contact_resolution_rejects_cross_company_identity(qualification_db):
    db, org, _ = qualification_db
    service = ResponseQualificationService()
    first = make_company(db, org, "First")
    second = make_company(db, org, "Second")
    contact = CompanyContact(organization_id=org.id, company_id=first.id, full_name="Shared", department=ContactDepartment.OTHER, seniority=ContactSeniority.UNKNOWN)
    db.add(contact)
    db.flush()
    db.add(CompanyContactMethod(contact_id=contact.id, method_type=ContactMethodType.EMAIL, value="shared@example.com", normalized_value="shared@example.com"))
    db.commit()
    result = service.resolve_contact(db, second.id, ContactResolutionRequest(email="shared@example.com"))
    assert result["result"] == "NO_MATCH"