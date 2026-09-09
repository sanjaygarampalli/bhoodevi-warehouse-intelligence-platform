"""Central policy for deterministic warehouse matching (not an AI model)."""
from enum import Enum
from types import MappingProxyType

from app.models.warehouse import AvailabilityStatus


class WarehouseMatchLevel(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    PARTIAL = "PARTIAL"
    POOR = "POOR"


SCORING_VERSION = "warehouse-rules-v1"
ENGINE_ID = "bwip-warehouse-rules"
WEIGHTS = MappingProxyType({"location": 30, "capacity": 35, "availability": 20, "type": 15})
LEVEL_THRESHOLDS = (
    (80, WarehouseMatchLevel.EXCELLENT),
    (60, WarehouseMatchLevel.GOOD),
    (40, WarehouseMatchLevel.PARTIAL),
    (0, WarehouseMatchLevel.POOR),
)
ELIGIBLE_STATUSES = (AvailabilityStatus.AVAILABLE, AvailabilityStatus.PARTIALLY_OCCUPIED)
CAPACITY_FAILURE_CAP = 39
UNVERIFIED_VACANCY_CAP = 59
TYPE_MISMATCH_CAP = 59
UNKNOWN_TYPE_CAP = 79
LOCATION_MISMATCH_CAP = 79
INELIGIBLE_CAP = 39
CITY_FALLBACK_POINTS = 20
STATE_FALLBACK_POINTS = 10
OVERSIZE_CAPACITY_POINTS = 25
PARTIAL_AVAILABILITY_POINTS = 10
OVERSIZE_RATIO = 2
CANDIDATE_BATCH_SIZE = 200
MAX_RESULTS = 100

# These are not evaluated in Phase 1. Some (e.g. technical and lease fields)
# need agreed unit/semantic rules; others lack structured warehouse counterparts.
# Do not parse free text or manufacture suitability or amenity guarantees.
UNSUPPORTED_REQUIREMENT_FIELDS = (
    "preferred_locality", "radius_km", "latitude", "longitude", "industry",
    "goods_type", "storage_type", "compliance_requirements", "budget_per_sqft",
    "lease_duration_months", "security_deposit_months", "preferred_lease_type",
    "escalation_percentage", "required_clear_height", "required_floor_load",
    "required_power_load", "required_docks", "truck_parking_required",
    "rail_connectivity_required", "fire_noc_required", "temperature_controlled",
    "loading_bays_required", "dock_level_required", "ground_level_required",
    "office_required", "labour_required", "operating_hours",
    "expected_monthly_dispatch", "expected_monthly_receipts", "move_in_timeframe",
)


def classify_match(score: int) -> WarehouseMatchLevel:
    if not 0 <= score <= 100:
        raise ValueError("Match score must be between 0 and 100")
    return next(level for threshold, level in LEVEL_THRESHOLDS if score >= threshold)