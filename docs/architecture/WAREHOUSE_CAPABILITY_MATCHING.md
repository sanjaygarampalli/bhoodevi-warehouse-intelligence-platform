# Warehouse Capability Matching

## Scope

Module 2 describes warehouse capabilities and compares them with an explicitly recorded company warehouse requirement. It is deterministic matching, not AI prediction: the platform does not invent requirements, infer missing facts, or claim planned facilities are available.

## Profiles

`WarehouseCapabilityProfile` is one organization-scoped profile per warehouse. Its normalized capability map stores a value and one of `CONFIRMED`, `PLANNED`, `UNKNOWN`, or `NOT_AVAILABLE`. It covers space, physical specifications, access, utilities, and special capabilities without adding empty columns for facts a warehouse cannot yet provide.

`CompanyWarehouseRequirementProfile` is one organization-scoped profile per company. Each requirement stores a value and `MANDATORY`, `IMPORTANT`, or `PREFERRED` priority. Existing lead `Requirement` and the existing ranked `WarehouseMatch` engine are not replaced.

## Scoring rules

Each requirement contributes 50 points for MANDATORY, 30 for IMPORTANT, or 20 for PREFERRED. The current score is the percentage of weighted points satisfied by confirmed capabilities. A confirmed value must meet the requested value (numeric values are minimums; other values are case-insensitive exact matches). Classification thresholds are EXCELLENT >= 80, GOOD >= 60, PARTIAL >= 40, and POOR below 40.

Any unsatisfied MANDATORY requirement sets `mandatory_gap=true` and forces `NOT_SUITABLE`, regardless of the score. Factor results expose the requirement, warehouse value, priority, status, and score impact.

Planned capabilities produce `PLANNED_IMPROVEMENT`, earn zero current points, and are returned in `planned_capabilities`. They are never mixed into the current score or treated as satisfying a current mandatory requirement. No future score is presented.

## Security and limitations

New profile and evaluation operations require both records to belong to the requesting organization; cross-organization evaluation returns 403. Legacy warehouse rows may have a null organization during migration compatibility, and therefore cannot be used by the new tenant-scoped workflow until assigned an organization. This module does not perform lease negotiation, inventory management, route optimization, AI prediction, or automatic commercial commitments.