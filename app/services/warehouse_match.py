from decimal import Decimal, InvalidOperation
from heapq import heappush, heapreplace
import json

from sqlalchemy.orm import Session
from app.services.deal_workflow import protect_deal_reference

from app.models.requirement import Requirement, RequirementStatus, WarehouseType
from app.models.warehouse import AvailabilityStatus, Warehouse
from app.models.warehouse_match import MatchedBy, WarehouseMatch, WarehouseMatchStatus
from app.repositories.lead import LeadRepository
from app.repositories.requirement import RequirementRepository
from app.repositories.warehouse import WarehouseRepository
from app.repositories.warehouse_match import WarehouseMatchRepository
from app.schemas.warehouse_match import (
    WarehouseMatchAdjustment, WarehouseMatchCreate, WarehouseMatchReason,
    WarehouseMatchRecommendationResponse, WarehouseMatchResult, WarehouseMatchUpdate,
    WarehouseMatchGenerationResponse,
)
from app.services import warehouse_matching_rules as rules


def _normalized(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _number(value) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def evaluate_warehouse_match(requirement: Requirement, warehouse: Warehouse) -> WarehouseMatchResult:
    """Pure evaluation of scalar fields. Never reads relationships or mutates input."""
    reasons: list[WarehouseMatchReason] = []
    warnings: list[str] = []
    caps: list[tuple[str, int, str]] = []

    def reason(factor: str, points: int, explanation: str) -> None:
        reasons.append(WarehouseMatchReason(
            factor=factor, points=points, maximum_points=rules.WEIGHTS[factor],
            explanation=explanation,
        ))

    def cap(factor: str, value: int, explanation: str) -> None:
        caps.append((factor, value, explanation))
        warnings.append(explanation)

    # Compare every supplied structured location; contradictory state/city data
    # must not be hidden by an otherwise equal pincode. No fuzzy or GIS matching.
    locations = [
        ("state", _normalized(requirement.preferred_state), _normalized(warehouse.state)),
        ("city", _normalized(requirement.preferred_city), _normalized(warehouse.city)),
        ("pincode", _normalized(requirement.preferred_pincode), _normalized(warehouse.postal_code)),
    ]
    supplied = [(name, wanted, actual) for name, wanted, actual in locations if wanted]
    mismatch = [(name, wanted, actual) for name, wanted, actual in supplied if wanted != actual]
    if not supplied:
        reason("location", 0, "No preferred state, city or pincode was supplied.")
    elif not mismatch:
        reason("location", rules.WEIGHTS["location"], "All supplied structured location preferences match: " + ", ".join(name for name, _, _ in supplied) + ".")
    else:
        matches = {name for name, wanted, actual in supplied if wanted == actual}
        state_conflict = any(name == "state" for name, _, _ in mismatch)
        city_conflict = any(name == "city" for name, _, _ in mismatch)
        points = 0
        if "city" in matches and not state_conflict:
            points = rules.CITY_FALLBACK_POINTS
        elif "state" in matches:
            points = rules.STATE_FALLBACK_POINTS
        # Pincode alone must never override a conflicting city or state.
        if state_conflict or (city_conflict and "state" not in matches):
            points = 0
        details = "; ".join(
            f"{name}: requested '{wanted}', warehouse '{actual or 'unknown'}'"
            for name, wanted, actual in mismatch
        )
        reason("location", points, "Location preferences not fully satisfied; " + details + ".")
        cap("location", rules.LOCATION_MISMATCH_CAP, "Location mismatch or missing warehouse location: " + details + ".")

    # Requirement areas are interpreted as square feet, matching the warehouse
    # columns. Never substitute open area for built-up area or infer vacant area.
    area_fields = ("minimum_area", "maximum_area", "required_builtup_area", "required_open_area")
    areas = {name: _number(getattr(requirement, name)) for name in area_fields}
    invalid = [name for name in area_fields if getattr(requirement, name) is not None and (
        areas[name] is None or (name in ("minimum_area", "maximum_area") and areas[name] == 0)
    )]
    minimum, maximum = areas["minimum_area"], areas["maximum_area"]
    builtup, open_area = areas["required_builtup_area"], areas["required_open_area"]
    component_total = (builtup or Decimal(0)) + (open_area or Decimal(0))
    if maximum is not None and ((minimum is not None and minimum > maximum) or component_total > maximum):
        invalid.append("contradictory area bounds")
    checks: list[tuple[str, Decimal, Decimal | None]] = []
    for name, wanted, actual in (
        ("built-up area", builtup, warehouse.built_up_area_sqft),
        ("open area", open_area, warehouse.open_area_sqft),
        ("total area", minimum, warehouse.total_area_sqft),
    ):
        if wanted is not None and wanted > 0:
            checks.append((name, wanted, _number(actual)))
    # A known total below combined component demand is physically impossible,
    # even if inconsistent component columns individually claim enough space.
    total = _number(warehouse.total_area_sqft)
    if component_total > 0 and total is not None and (minimum is None or component_total > minimum):
        checks.append(("total area for combined built-up/open demand", component_total, total))
    failures = [f"{name}: {actual} sqft is below required {wanted} sqft" for name, wanted, actual in checks if actual is not None and actual < wanted]
    unknown = [name for name, _, actual in checks if actual is None]
    if invalid:
        message = "Invalid requirement area data: " + ", ".join(invalid) + "."
        reason("capacity", 0, message)
        cap("capacity", rules.CAPACITY_FAILURE_CAP, message)
    elif failures:
        message = "Warehouse capacity is below the required minimum; " + "; ".join(failures) + "."
        reason("capacity", 0, message)
        cap("capacity", rules.CAPACITY_FAILURE_CAP, message)
    elif not checks:
        reason("capacity", 0, "No positive minimum, built-up or open area demand was supplied; capacity suitability is unknown.")
    elif unknown:
        message = "Cannot verify required capacity; missing or invalid warehouse " + ", ".join(unknown) + "."
        reason("capacity", 0, message)
        warnings.append(message)
    else:
        oversized = any(actual > wanted * rules.OVERSIZE_RATIO for _, wanted, actual in checks)
        above_maximum = maximum is not None and total is not None and total > maximum
        if maximum is not None and total is None:
            reason("capacity", 0, "Warehouse total area is unknown; the requested maximum cannot be checked.")
            warnings.append("Requested maximum area cannot be verified.")
        elif oversized or above_maximum:
            message = "Recorded physical areas satisfy minimum demand, but exceed the preferred maximum or twice a requested area; subdivision and commercial fit need verification."
            reason("capacity", rules.OVERSIZE_CAPACITY_POINTS, message)
            warnings.append(message)
        else:
            reason("capacity", rules.WEIGHTS["capacity"], "Recorded physical areas satisfy all supplied area bounds and minimum demands (sqft): " + "; ".join(f"{name} {actual} >= {wanted}" for name, wanted, actual in checks) + ".")

    status = warehouse.availability_status
    if status == AvailabilityStatus.AVAILABLE:
        reason("availability", rules.WEIGHTS["availability"], "Warehouse status is AVAILABLE; this is not a reservation or a move-in date guarantee.")
    elif status == AvailabilityStatus.PARTIALLY_OCCUPIED:
        reason("availability", rules.PARTIAL_AVAILABILITY_POINTS, "Warehouse is PARTIALLY_OCCUPIED; physical area is not verified vacant area.")
        cap("availability", rules.UNVERIFIED_VACANCY_CAP, "Vacant built-up/open area is not recorded; partially occupied stock requires capacity verification.")
    else:
        reason("availability", 0, "Warehouse status is unknown or ineligible for recommendations.")
        cap("availability", rules.INELIGIBLE_CAP, "Warehouse is not confirmed available or partially occupied.")
    occupancy = _number(warehouse.occupancy_rate)
    if warehouse.occupancy_rate is not None and (occupancy is None or occupancy > 100 or (status == AvailabilityStatus.AVAILABLE and occupancy > 0) or occupancy == 100):
        cap("availability", rules.UNVERIFIED_VACANCY_CAP, "Occupancy rate is invalid or conflicts with available capacity; vacant area must be verified.")
    if warehouse.available_from is not None:
        warnings.append("Warehouse available_from is recorded but move-in date compatibility is not evaluated in Phase 1.")

    requested_type, actual_type = requirement.warehouse_type, warehouse.warehouse_type
    if requested_type is None:
        reason("type", 0, "No structured warehouse type was requested.")
    elif actual_type is None:
        reason("type", 0, "Warehouse type is unknown; compatibility cannot be verified.")
        cap("type", rules.UNKNOWN_TYPE_CAP, "Requested warehouse type cannot be verified.")
    elif requested_type == WarehouseType.OTHER or actual_type == WarehouseType.OTHER:
        reason("type", 0, "OTHER does not establish a specific compatible warehouse type.")
        cap("type", rules.UNKNOWN_TYPE_CAP, "Warehouse type OTHER requires manual suitability verification.")
    elif requested_type == actual_type:
        reason("type", rules.WEIGHTS["type"], f"Structured warehouse type matches {requested_type.value}.")
    else:
        message = f"Warehouse type {actual_type.value} does not match requested {requested_type.value}; no type substitutions are assumed."
        reason("type", 0, message)
        cap("type", rules.TYPE_MISMATCH_CAP, message)

    score = sum(item.points for item in reasons)
    adjustments = []
    for factor, score_cap, explanation in caps:
        adjusted = min(score, score_cap)
        adjustments.append(WarehouseMatchAdjustment(
            factor=factor, points=adjusted - score, score_cap=score_cap, explanation=explanation,
        ))
        score = adjusted
    return WarehouseMatchResult(
        warehouse_id=warehouse.id, warehouse_name=warehouse.warehouse_name,
        match_score=score, match_level=rules.classify_match(score), reasons=reasons,
        adjustments=adjustments, warnings=warnings,
    )


def _requirement_warnings(requirement: Requirement) -> list[str]:
    warnings = []
    if requirement.requirement_status != RequirementStatus.ACTIVE:
        warnings.append("Requirement is not ACTIVE; results are advisory and do not change its workflow status.")
    unsupported = [name for name in rules.UNSUPPORTED_REQUIREMENT_FIELDS
                   if getattr(requirement, name) not in (None, "", False)]
    if unsupported:
        warnings.append("Supplied criteria not evaluated in Phase 1: " + ", ".join(unsupported) + ".")
    warnings.append("Scores measure supported criteria only, not confidence, verified vacant capacity or complete leasing suitability.")
    return warnings


class WarehouseMatchService:
    def __init__(self) -> None:
        self.repository = WarehouseMatchRepository()
        self.lead_repository = LeadRepository()
        self.warehouse_repository = WarehouseRepository()
        self.requirement_repository = RequirementRepository()

    def generate_matches_for_requirement(
        self, db: Session, requirement_id: int,
    ) -> WarehouseMatchGenerationResponse | None:
        """Atomically refresh engine-owned rows, never manual/reviewed decisions."""
        if db.new or db.dirty or db.deleted:
            raise ValueError("Generation requires a session without pending changes")
        try:
            requirement = self.repository.lock_requirement(db, requirement_id)
            if requirement is None:
                db.rollback()
                return None
            existing = {m.warehouse_id: m for m in
                        self.repository.get_generation_matches(db, requirement_id)}
            warehouses = self.repository.get_generation_warehouses(
                db, requirement_id, eligible_statuses=rules.ELIGIBLE_STATUSES,
            )
            warnings = _requirement_warnings(requirement)
            created = refreshed = stale = preserved = evaluated = 0
            ranked = []
            for warehouse in warehouses:
                match = existing.get(warehouse.id)
                eligible = warehouse.availability_status in rules.ELIGIBLE_STATUSES
                evaluated += int(eligible)
                result = evaluate_warehouse_match(requirement, warehouse)
                if match is not None and not (
                    match.model_id == rules.ENGINE_ID and match.matched_by == MatchedBy.AI
                    and match.status in (WarehouseMatchStatus.AI_RECOMMENDED, WarehouseMatchStatus.STALE)
                    and match.reviewed_by_user_id is None and match.reviewed_at is None
                ):
                    preserved += 1
                    continue
                if match is None:
                    match = WarehouseMatch(requirement_id=requirement.id, warehouse_id=warehouse.id,
                                           matched_by=MatchedBy.AI, model_id=rules.ENGINE_ID)
                    db.add(match)
                    created += 1
                elif eligible:
                    refreshed += 1
                match.lead_id = requirement.lead_id
                match.match_score = result.match_score
                match.match_rank = None
                match.model_version = rules.SCORING_VERSION
                match.status = WarehouseMatchStatus.AI_RECOMMENDED if eligible else WarehouseMatchStatus.STALE
                concerns = result.warnings + warnings
                if eligible:
                    ranked.append(match)
                else:
                    stale += 1
                    concerns = ["Warehouse is no longer eligible; this saved match is stale."] + concerns
                match.match_reasons = json.dumps([r.model_dump() for r in result.reasons], sort_keys=True)
                match.concern_reasons = json.dumps(concerns)
                match.requirement_compatibility = json.dumps({
                    "scoring_version": rules.SCORING_VERSION,
                    "match_level": result.match_level.value,
                    "adjustments": [a.model_dump() for a in result.adjustments],
                }, sort_keys=True)
                match.top_reason = max(result.reasons, key=lambda r: r.points).explanation
            for rank, match in enumerate(sorted(ranked, key=lambda m: (-m.match_score, m.warehouse_id)), 1):
                match.match_rank = rank
            response = WarehouseMatchGenerationResponse(
                requirement_id=requirement.id, scoring_version=rules.SCORING_VERSION,
                candidates_evaluated=evaluated, created=created, refreshed=refreshed,
                stale=stale, preserved=preserved, warnings=warnings + [
                    "Manual, reviewed and workflow-progressed matches are preserved; saved and live scores may differ."
                ],
            )
            db.commit()
            return response
        except Exception:
            db.rollback()
            raise

    def recommend_for_requirement(
        self, db: Session, requirement_id: int, *, limit: int = rules.MAX_RESULTS,
    ) -> WarehouseMatchRecommendationResponse | None:
        """Fresh, read-only recommendations; saved workflow fields are untouched."""
        if not 1 <= limit <= rules.MAX_RESULTS:
            raise ValueError(f"limit must be between 1 and {rules.MAX_RESULTS}")
        if db.new or db.dirty or db.deleted:
            raise ValueError("Recommendations require a session without pending changes")
        with db.no_autoflush:
            requirement = self.requirement_repository.get_by_id(db, requirement_id)
            if requirement is None:
                return None
            warnings = _requirement_warnings(requirement)
            best = []
            count = 0
            for warehouse, match_id, match_status in self.repository.iter_recommendation_candidates(
                db, requirement_id, eligible_statuses=rules.ELIGIBLE_STATUSES,
                batch_size=rules.CANDIDATE_BATCH_SIZE,
            ):
                result = evaluate_warehouse_match(requirement, warehouse)
                result.existing_match_id = match_id
                result.existing_match_status = match_status
                if match_status is not None:
                    result.warnings.append(
                        f"Existing saved match status is {match_status.value}; current suitability does not override this workflow decision."
                    )
                item = (result.match_score, -result.warehouse_id, result)
                if len(best) < limit:
                    heappush(best, item)
                elif item[:2] > best[0][:2]:
                    heapreplace(best, item)
                count += 1
            matches = [item[2] for item in sorted(best, key=lambda item: (-item[0], -item[1]))]
            for rank, result in enumerate(matches, start=1):
                result.match_rank = rank
            return WarehouseMatchRecommendationResponse(
                requirement_id=requirement.id, lead_id=requirement.lead_id,
                scoring_version=rules.SCORING_VERSION, candidates_evaluated=count,
                limit=limit, matches=matches, warnings=warnings,
            )

    def create_match(
        self,
        db: Session,
        match_data: WarehouseMatchCreate,
    ) -> WarehouseMatch | None:
        lead = self.lead_repository.get_by_id(db, match_data.lead_id)
        if lead is None:
            return None

        warehouse = self.warehouse_repository.get_by_id(db, match_data.warehouse_id)
        if warehouse is None:
            return None

        if match_data.requirement_id is not None:
            requirement = self.requirement_repository.get_by_id(
                db,
                match_data.requirement_id,
            )
            if requirement is None:
                return None

        db_match = WarehouseMatch(**match_data.model_dump())
        return self.repository.create(db, db_match)

    def get_match_by_id(
        self,
        db: Session,
        match_id: int,
    ) -> WarehouseMatch | None:
        return self.repository.get_by_id(db, match_id)

    def list_matches_for_lead(
        self,
        db: Session,
        lead_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WarehouseMatch]:
        return self.repository.get_matches_for_lead(
            db,
            lead_id,
            limit=limit,
            offset=offset,
        )

    def list_matches_for_warehouse(
        self,
        db: Session,
        warehouse_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WarehouseMatch]:
        return self.repository.get_matches_for_warehouse(
            db,
            warehouse_id,
            limit=limit,
            offset=offset,
        )

    def list_matches_for_requirement(
        self,
        db: Session,
        requirement_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WarehouseMatch]:
        return self.repository.get_matches_for_requirement(
            db,
            requirement_id,
            limit=limit,
            offset=offset,
        )

    def update_match(
        self,
        db: Session,
        match_id: int,
        match_data: WarehouseMatchUpdate,
    ) -> WarehouseMatch | None:
        db_match = self.repository.get_by_id(db, match_id)
        if db_match is None:
            return None

        update_data = match_data.model_dump(exclude_unset=True)

        if any(field in update_data and update_data[field] != getattr(db_match, field)
               for field in ("lead_id", "requirement_id", "warehouse_id")):
            protect_deal_reference(db, "match", match_id)

        if "lead_id" in update_data and update_data["lead_id"] != db_match.lead_id:
            lead = self.lead_repository.get_by_id(db, update_data["lead_id"])
            if lead is None:
                return None

        if "warehouse_id" in update_data and update_data["warehouse_id"] != db_match.warehouse_id:
            warehouse = self.warehouse_repository.get_by_id(
                db,
                update_data["warehouse_id"],
            )
            if warehouse is None:
                return None

        if "requirement_id" in update_data:
            requirement_id = update_data["requirement_id"]
            if requirement_id is None:
                db_match.requirement_id = None
            else:
                requirement = self.requirement_repository.get_by_id(
                    db,
                    requirement_id,
                )
                if requirement is None:
                    return None
                db_match.requirement_id = requirement_id

        for key, value in update_data.items():
            if key == "requirement_id":
                continue
            setattr(db_match, key, value)

        return self.repository.update(db, db_match)

    def delete_match(
        self,
        db: Session,
        match_id: int,
    ) -> WarehouseMatch | None:
        db_match = self.repository.get_by_id(db, match_id)
        if db_match is None:
            return None

        protect_deal_reference(db, "match", match_id)
        self.repository.delete(db, db_match)
        return db_match