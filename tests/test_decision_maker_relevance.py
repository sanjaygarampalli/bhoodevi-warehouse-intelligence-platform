from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.db.base import Base
from app.models.company_intelligence import (
    CompanyContact,
    CompanyContactMethod,
    ContactDepartment,
    ContactMethodType,
    ContactSeniority,
)
from app.services.decision_maker_relevance import DecisionMakerRelevanceService

from tests.test_company_intelligence_foundation import isolated_company_api


def _contact(db, company, name, title, department, seniority):
    contact = CompanyContact(
        organization_id=company.organization_id,
        company_id=company.id,
        full_name=name,
        job_title=title,
        department=department,
        seniority=seniority,
    )
    db.add(contact)
    db.flush()
    return contact


def test_functional_relevance_and_seniority_do_not_override_function(isolated_company_api):
    db, _, company, *_ = isolated_company_api
    logistics = _contact(db, company, "Head Logistics", "Head of Logistics", ContactDepartment.LOGISTICS, ContactSeniority.HEAD)
    marketing = _contact(db, company, "Chief Marketing", "Chief Marketing Officer", ContactDepartment.OTHER, ContactSeniority.C_LEVEL)
    db.commit()

    result = DecisionMakerRelevanceService().assess_company(db, company.id, company.organization_id)
    by_name = {item.contact.full_name: item for item in result["contacts"]}
    assert by_name[logistics.full_name].relevance.value == "HIGH"
    assert by_name[logistics.full_name].relevance_score > by_name[marketing.full_name].relevance_score
    assert any("warehouse" in reason.lower() or "logistics" in reason.lower() for reason in by_name[logistics.full_name].reasons)
    assert by_name[logistics.full_name].human_review_required is True
    assert "not a confirmed decision-maker fact" in by_name[logistics.full_name].inference


def test_completeness_is_separate_from_relevance_and_order_is_stable(isolated_company_api):
    db, _, company, *_ = isolated_company_api
    relevant = _contact(db, company, "Operations Lead", "Warehouse Operations Manager", ContactDepartment.OPERATIONS, ContactSeniority.MANAGER)
    irrelevant = _contact(db, company, "Marketing Manager", "Marketing Manager", ContactDepartment.OTHER, ContactSeniority.MANAGER)
    db.add(CompanyContactMethod(contact_id=irrelevant.id, method_type=ContactMethodType.EMAIL, value="marketing@example.com", normalized_value="marketing@example.com"))
    db.commit()

    service = DecisionMakerRelevanceService()
    first = service.assess_company(db, company.id, company.organization_id)
    second = service.assess_company(db, company.id, company.organization_id)
    assert [item.contact.id for item in first["contacts"]] == [item.contact.id for item in second["contacts"]]
    high = next(item for item in first["contacts"] if item.contact.id == relevant.id)
    full_but_irrelevant = next(item for item in first["contacts"] if item.contact.id == irrelevant.id)
    assert high.relevance.value == "HIGH"
    assert high.contact_methods["has_email"] is False
    assert high.contactability_status == "LIMITED CONTACT INFORMATION"
    assert full_but_irrelevant.contact_methods["has_email"] is True
    assert full_but_irrelevant.relevance.value != "HIGH"


def test_queue_and_company_endpoint_are_organization_safe(isolated_company_api):
    db, client, company, *_ = isolated_company_api
    _contact(db, company, "A Logistics", "Head of Supply Chain", ContactDepartment.SUPPLY_CHAIN, ContactSeniority.HEAD)
    db.commit()
    service = DecisionMakerRelevanceService()
    queue = service.queue(db, company.organization_id)
    assert queue.total == 2  # fixture contact plus the added contact
    assert all(item.assessment.contact.organization_id == company.organization_id for item in queue.items)
    response = client.get(f"/companies/{company.id}/decision-maker-priorities")
    assert response.status_code == 403  # the fixture user belongs only to the other organization


def test_empty_company_assessment_is_read_only_and_human_reviewed(isolated_company_api):
    db, _, company, *_ = isolated_company_api
    db.query(CompanyContact).filter(CompanyContact.company_id == company.id).delete()
    db.commit()
    result = DecisionMakerRelevanceService().assess_company(db, company.id, company.organization_id)
    assert result["contacts"] == []
    assert result["total"] == 0
    assert result["human_review_required"] is True