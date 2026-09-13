from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.warehouse import Warehouse
from app.models.warehouse_capability import CapabilityStatus, WarehouseCapabilityProfile
from app.models.warehouse_requirement import CompanyWarehouseRequirementProfile

WEIGHTS = {"MANDATORY": 50, "IMPORTANT": 30, "PREFERRED": 20}


def _satisfies(required: Any, actual: Any) -> bool:
    if required is None or actual is None:
        return False
    if isinstance(required, bool):
        return actual is required
    try:
        if isinstance(required, (int, float, Decimal)) and isinstance(actual, (int, float, Decimal)):
            return actual >= required
    except TypeError:
        pass
    return str(actual).strip().casefold() == str(required).strip().casefold()


def evaluate_capability_match(capabilities: dict, requirements: dict, warehouse_id: int, company_id: int) -> dict:
    factors = []
    missing = []
    planned = []
    earned = 0
    total = sum(WEIGHTS[item.get("priority", "PREFERRED")] for item in requirements.values()) or 1
    for factor, requirement in requirements.items():
        priority = requirement.get("priority", "PREFERRED")
        requested = requirement.get("value")
        capability = capabilities.get(factor, {"value": None, "status": CapabilityStatus.UNKNOWN.value})
        actual = capability.get("value")
        status = capability.get("status", CapabilityStatus.UNKNOWN.value)
        if status == CapabilityStatus.CONFIRMED.value and _satisfies(requested, actual):
            result_status, points = "SATISFIED", WEIGHTS[priority]
            earned += points
            explanation = "Confirmed warehouse capability satisfies the requirement."
        elif status == CapabilityStatus.PLANNED.value and _satisfies(requested, actual):
            result_status, points = "PLANNED_IMPROVEMENT", 0
            planned.append(factor)
            explanation = "Planned capability may satisfy the requirement in future, but is not currently available."
        elif status == CapabilityStatus.NOT_AVAILABLE.value:
            result_status, points = "NOT_AVAILABLE", 0
            explanation = "The capability is explicitly not available."
        else:
            result_status, points = "UNKNOWN", 0
            explanation = "The capability is unknown or does not satisfy the requirement."
        if priority == "MANDATORY" and result_status != "SATISFIED":
            missing.append(factor)
        factors.append({"factor": factor, "requirement": requested, "warehouse_value": actual,
                        "priority": priority, "status": result_status, "score_impact": points,
                        "explanation": explanation})
    score = round(100 * earned / total)
    if missing:
        classification = "NOT_SUITABLE"
    elif score >= 80:
        classification = "EXCELLENT"
    elif score >= 60:
        classification = "GOOD"
    elif score >= 40:
        classification = "PARTIAL"
    else:
        classification = "POOR"
    return {"warehouse_id": warehouse_id, "company_id": company_id, "current_match_score": score,
            "classification": classification, "mandatory_gap": bool(missing),
            "missing_mandatory_requirements": missing, "planned_capabilities": planned,
            "factor_results": factors,
            "explanation": "Mandatory gaps are never hidden by the weighted score." if missing else "Score is the weighted sum of satisfied confirmed capabilities."}


class WarehouseCapabilityMatchingService:
    def _warehouse(self, db: Session, warehouse_id: int, organization_id: int):
        return db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.organization_id == organization_id))

    def _company(self, db: Session, company_id: int, organization_id: int):
        return db.scalar(select(Company).where(Company.id == company_id, Company.organization_id == organization_id))

    def get_capability(self, db: Session, warehouse_id: int, organization_id: int):
        if self._warehouse(db, warehouse_id, organization_id) is None:
            return None
        return db.scalar(select(WarehouseCapabilityProfile).where(WarehouseCapabilityProfile.warehouse_id == warehouse_id,
                                                                   WarehouseCapabilityProfile.organization_id == organization_id))

    def save_capability(self, db: Session, warehouse_id: int, organization_id: int, capabilities: dict, create: bool = False):
        if self._warehouse(db, warehouse_id, organization_id) is None:
            return None
        profile = self.get_capability(db, warehouse_id, organization_id)
        if profile is None:
            if not create:
                return None
            profile = WarehouseCapabilityProfile(warehouse_id=warehouse_id, organization_id=organization_id)
        elif not create:
            profile.capabilities = {**profile.capabilities, **capabilities}
            capabilities = profile.capabilities
        profile.capabilities = capabilities
        db.add(profile); db.commit(); db.refresh(profile)
        return profile

    def get_requirement(self, db: Session, company_id: int, organization_id: int):
        if self._company(db, company_id, organization_id) is None:
            return None
        return db.scalar(select(CompanyWarehouseRequirementProfile).where(CompanyWarehouseRequirementProfile.company_id == company_id,
                                                                          CompanyWarehouseRequirementProfile.organization_id == organization_id))

    def save_requirement(self, db: Session, company_id: int, organization_id: int, requirements: dict, create: bool = False):
        if self._company(db, company_id, organization_id) is None:
            return None
        profile = self.get_requirement(db, company_id, organization_id)
        if profile is None:
            if not create:
                return None
            profile = CompanyWarehouseRequirementProfile(company_id=company_id, organization_id=organization_id)
        elif not create:
            profile.requirements = {**profile.requirements, **requirements}
            requirements = profile.requirements
        profile.requirements = requirements
        db.add(profile); db.commit(); db.refresh(profile)
        return profile

    def evaluate(self, db: Session, warehouse_id: int, company_id: int, organization_id: int):
        warehouse = self._warehouse(db, warehouse_id, organization_id)
        company = self._company(db, company_id, organization_id)
        if warehouse is None or company is None:
            return None
        capabilities = self.get_capability(db, warehouse_id, organization_id)
        requirements = self.get_requirement(db, company_id, organization_id)
        return evaluate_capability_match(capabilities.capabilities if capabilities else {}, requirements.requirements if requirements else {}, warehouse_id, company_id)