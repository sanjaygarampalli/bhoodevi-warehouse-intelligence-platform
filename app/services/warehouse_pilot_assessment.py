from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.warehouse import Warehouse
from app.models.warehouse_pilot import (
    ListingStatus, OperationalStatus, WarehouseCommercialProfile,
    WarehouseOperationalProfile, WarehouseRequirementAssessment,
)
from app.services.warehouse_capability_matching import evaluate_capability_match
from app.models.warehouse_capability import WarehouseCapabilityProfile
from app.models.warehouse_requirement import CompanyWarehouseRequirementProfile


class WarehousePilotService:
    def _warehouse(self, db, warehouse_id, organization_id):
        return db.scalar(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.organization_id == organization_id))

    def _company(self, db, company_id, organization_id):
        return db.scalar(select(Company).where(Company.id == company_id, Company.organization_id == organization_id))

    def get_operational(self, db, warehouse_id, organization_id):
        if not self._warehouse(db, warehouse_id, organization_id): return None
        return db.scalar(select(WarehouseOperationalProfile).where(WarehouseOperationalProfile.warehouse_id == warehouse_id, WarehouseOperationalProfile.organization_id == organization_id))

    def save_operational(self, db, warehouse_id, organization_id, values, create=False):
        if not self._warehouse(db, warehouse_id, organization_id): return None
        profile = self.get_operational(db, warehouse_id, organization_id)
        if profile is None:
            if not create: return None
            profile = WarehouseOperationalProfile(warehouse_id=warehouse_id, organization_id=organization_id)
        for key, value in values.items(): setattr(profile, key, value)
        db.add(profile); db.commit(); db.refresh(profile); return profile

    def get_commercial(self, db, warehouse_id, organization_id):
        if not self._warehouse(db, warehouse_id, organization_id): return None
        return db.scalar(select(WarehouseCommercialProfile).where(WarehouseCommercialProfile.warehouse_id == warehouse_id, WarehouseCommercialProfile.organization_id == organization_id))

    def save_commercial(self, db, warehouse_id, organization_id, values, create=False):
        warehouse = self._warehouse(db, warehouse_id, organization_id)
        if not warehouse: return None
        profile = self.get_commercial(db, warehouse_id, organization_id)
        if profile is None:
            if not create: return None
            profile = WarehouseCommercialProfile(warehouse_id=warehouse_id, organization_id=organization_id)
        if not create:
            values = {**{key: getattr(profile, key) for key in values}, **values}
        for key, value in values.items(): setattr(profile, key, value)
        db.add(profile); db.commit(); db.refresh(profile); return profile

    def get_requirement_assessment(self, db, company_id, organization_id):
        if not self._company(db, company_id, organization_id): return None
        return db.scalar(select(WarehouseRequirementAssessment).where(WarehouseRequirementAssessment.company_id == company_id, WarehouseRequirementAssessment.organization_id == organization_id))

    def save_requirement_assessment(self, db, company_id, organization_id, values, create=False):
        company = self._company(db, company_id, organization_id)
        if not company: return None
        if values.get("validation_status") == "VALIDATED":
            values = {**values, "validated_at": datetime.utcnow()}
        assessment = self.get_requirement_assessment(db, company_id, organization_id)
        if assessment is None:
            if not create: return None
            assessment = WarehouseRequirementAssessment(company_id=company_id, organization_id=organization_id)
        if not create:
            values = {**{key: getattr(assessment, key) for key in values}, **values}
        for key, value in values.items(): setattr(assessment, key, value)
        db.add(assessment); db.commit(); db.refresh(assessment); return assessment

    def evaluate(self, db: Session, warehouse_id: int, company_id: int, organization_id: int):
        warehouse = self._warehouse(db, warehouse_id, organization_id)
        company = self._company(db, company_id, organization_id)
        if warehouse is None or company is None: raise HTTPException(404, "Warehouse or company not found")
        capability = db.scalar(select(WarehouseCapabilityProfile).where(WarehouseCapabilityProfile.warehouse_id == warehouse_id, WarehouseCapabilityProfile.organization_id == organization_id))
        requirement = db.scalar(select(CompanyWarehouseRequirementProfile).where(CompanyWarehouseRequirementProfile.company_id == company_id, CompanyWarehouseRequirementProfile.organization_id == organization_id))
        technical = evaluate_capability_match(capability.capabilities if capability else {}, requirement.requirements if requirement else {}, warehouse_id, company_id)
        commercial = self.get_commercial(db, warehouse_id, organization_id)
        captured = self.get_requirement_assessment(db, company_id, organization_id)
        commercial_reasons = []
        commercial_fit = "UNKNOWN"
        if commercial:
            if commercial.expected_rent_per_sqft is None or commercial.available_area_sqft is None: commercial_reasons.append("Rent and available area are incomplete.")
            if captured and captured.preferred_rent_per_sqft is not None and commercial.expected_rent_per_sqft is not None and commercial.expected_rent_per_sqft > captured.preferred_rent_per_sqft:
                commercial_fit = "NOT_SUITABLE" if not commercial.rent_negotiable else "PARTIAL"
                commercial_reasons.append("Expected rent exceeds the captured preference." )
            elif captured and captured.preferred_lease_months and commercial.lease_term_min_months and captured.preferred_lease_months < commercial.lease_term_min_months:
                commercial_fit = "PARTIAL" if commercial.lease_term_negotiable else "NOT_SUITABLE"
                commercial_reasons.append("Preferred lease term is below the warehouse minimum.")
            elif commercial.expected_rent_per_sqft is not None and commercial.available_area_sqft is not None: commercial_fit = "CONFIRMED"
            else: commercial_fit = "PARTIAL"
        else: commercial_reasons.append("No commercial profile is recorded.")
        availability_reasons = []
        availability_fit = "UNKNOWN"
        if commercial:
            if commercial.listing_status in {ListingStatus.OCCUPIED, ListingStatus.RESERVED, ListingStatus.INACTIVE}: availability_fit = "NOT_SUITABLE"; availability_reasons.append(f"Listing status is {commercial.listing_status.value}.")
            elif captured and captured.move_in_target_date and commercial.available_from and commercial.available_from > captured.move_in_target_date: availability_fit = "PARTIAL"; availability_reasons.append("Warehouse becomes available after the target move-in date.")
            else: availability_fit = "CONFIRMED"; availability_reasons.append("Warehouse is listed for potential availability.")
        operational = self.get_operational(db, warehouse_id, organization_id)
        operational_reasons = []
        if not operational or operational.operational_status is None: readiness = "UNKNOWN"; operational_reasons.append("Operational readiness is not confirmed.")
        elif operational.operational_status == OperationalStatus.READY: readiness = "READY"; operational_reasons.append("Operational profile records READY.")
        elif operational.operational_status == OperationalStatus.PARTIALLY_READY: readiness = "PARTIALLY_READY"; operational_reasons.append("Operational profile records PARTIALLY_READY.")
        elif operational.operational_status == OperationalStatus.UNDER_PREPARATION: readiness = "REQUIRES_IMPROVEMENT"; operational_reasons.append("Facility is under preparation; planned improvements are not current capability.")
        else: readiness = "NOT_READY"; operational_reasons.append(f"Operational status is {operational.operational_status.value}.")
        confidence = captured.requirement_confidence.value if captured else "UNVERIFIED"
        blockers = bool(technical["mandatory_gap"] or commercial_fit == "NOT_SUITABLE" or availability_fit == "NOT_SUITABLE")
        strong_technical = technical["classification"] in {"EXCELLENT", "GOOD"}
        readiness_needs_work = readiness in {"REQUIRES_IMPROVEMENT", "PARTIALLY_READY"}
        incomplete_commercial_fit = commercial_fit in {"PARTIAL", "UNKNOWN"}
        incomplete_availability_fit = availability_fit in {"PARTIAL", "UNKNOWN"}
        if blockers:
            overall = "NOT_SUITABLE"
        elif (
            strong_technical
            and commercial_fit == "CONFIRMED"
            and availability_fit == "CONFIRMED"
            and readiness == "READY"
        ):
            overall = "STRONG_FIT"
        elif (
            (strong_technical and readiness_needs_work)
            or incomplete_commercial_fit
            or incomplete_availability_fit
        ):
            overall = "CONDITIONAL_FIT"
        elif technical["classification"] in {"EXCELLENT", "GOOD"}: overall = "POTENTIAL_FIT"
        else: overall = "WEAK_FIT"
        explanation = [technical["explanation"], *commercial_reasons, *availability_reasons, *operational_reasons]
        return {"warehouse_id": warehouse_id, "company_id": company_id, "technical_score": technical["current_match_score"], "technical_classification": technical["classification"], "mandatory_gaps": technical["missing_mandatory_requirements"], "planned_capabilities": technical["planned_capabilities"], "factor_results": technical["factor_results"], "commercial_fit": commercial_fit, "commercial_reasons": commercial_reasons, "availability_fit": availability_fit, "availability_reasons": availability_reasons, "operational_readiness": readiness, "operational_reasons": operational_reasons, "requirement_confidence": confidence, "overall_classification": overall, "explanation": explanation}