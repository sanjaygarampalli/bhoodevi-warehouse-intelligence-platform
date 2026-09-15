from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Company, Organization, OrganizationMembership, User
from app.models.company_intelligence import CompanyContact, ContactDepartment, ContactSeniority
from app.models.organization import OrgType, OrganizationStatus, SubscriptionTier
from app.models.organization_membership import MembershipStatus, OrganizationMemberRole
from app.models.contact_workflow import ContactOutreachMethod, InvestigationStatus, OutreachOutcome
from app.schemas.contact_workflow import InvestigationWrite, OutreachWrite
from app.services.contact_workflow import ContactWorkflowService
from app.services.organization_access import require_organization_write


@pytest.fixture()
def workflow_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    org = Organization(public_id="workflow-org", org_code="WF", legal_name="Workflow Org", org_type=OrgType.PVT_LTD, subscription_tier=SubscriptionTier.FREE, status=OrganizationStatus.ACTIVE)
    user = User(full_name="Researcher", email="workflow@example.com", role="user", hashed_password="unused")
    db.add_all([org, user]); db.flush()
    db.add(OrganizationMembership(user_id=user.id, organization_id=org.id, role=OrganizationMemberRole.MEMBER))
    company = Company(organization_id=org.id, company_name="Warehouse Prospect", industry="Logistics", company_type="PVT_LTD")
    db.add(company); db.flush()
    contact = CompanyContact(organization_id=org.id, company_id=company.id, full_name="Decision Contact", department=ContactDepartment.LOGISTICS, seniority=ContactSeniority.DIRECTOR)
    db.add(contact); db.commit()
    yield db, org, user, company, contact
    db.close(); Base.metadata.drop_all(engine); engine.dispose()


def test_investigation_selection_and_multiple_history(workflow_db):
    db, _, user, company, contact = workflow_db
    service = ContactWorkflowService()
    investigation = service.save_investigation(db, company.id, contact.id, user.id, InvestigationWrite(investigation_status=InvestigationStatus.VERIFIED, research_notes="Human observation"))
    assert investigation.selected_for_outreach is False
    selected = service.select_for_outreach(db, company.id, contact.id, user.id)
    assert selected.selected_for_outreach is True
    for method, when in ((ContactOutreachMethod.EMAIL, datetime(2026, 9, 1)), (ContactOutreachMethod.PHONE, datetime(2026, 9, 4)), (ContactOutreachMethod.EMAIL, datetime(2026, 9, 10))):
        service.create_outreach(db, company.id, contact.id, user.id, OutreachWrite(method=method, performed_at=when, outcome=OutreachOutcome.INTERESTED if when.day == 10 else OutreachOutcome.NO_RESPONSE))
    history = service.history(db, company.id, contact.id)[1]
    assert [item.performed_at.day for item in history] == [10, 4, 1]
    assert not db.query(Company).filter(Company.id == company.id).count() == 0


def test_foreign_company_contact_is_rejected(workflow_db):
    db, org, user, company, contact = workflow_db
    other = Company(organization_id=org.id, company_name="Other", industry="Logistics", company_type="PVT_LTD")
    db.add(other); db.commit()
    with pytest.raises(LookupError):
        ContactWorkflowService().create_outreach(db, other.id, contact.id, user.id, OutreachWrite(method=ContactOutreachMethod.EMAIL, performed_at=datetime.utcnow()))


def test_pipeline_context_is_awareness_not_a_block(workflow_db):
    db, _, user, company, contact = workflow_db
    context = ContactWorkflowService().pipeline_context(db, company.id)
    assert context["active_pipeline_exists"] is False
    activity = ContactWorkflowService().create_outreach(db, company.id, contact.id, user.id, OutreachWrite(method=ContactOutreachMethod.EMAIL, performed_at=datetime.utcnow(), outcome=OutreachOutcome.INTERESTED))
    assert activity.outcome == OutreachOutcome.INTERESTED.value


def test_viewer_and_inactive_membership_cannot_write(workflow_db):
    db, org, user, _, _ = workflow_db
    membership = db.query(OrganizationMembership).filter_by(user_id=user.id, organization_id=org.id).one()
    membership.role = OrganizationMemberRole.VIEWER
    db.commit()
    with pytest.raises(HTTPException):
        require_organization_write(db, user, org.id)
    membership.role = OrganizationMemberRole.MEMBER
    membership.status = MembershipStatus.INACTIVE
    db.commit()
    with pytest.raises(HTTPException):
        require_organization_write(db, user, org.id)