# Warehouse Matching Intelligence — Phase 1

## Existing architecture and integration decision

`WarehouseMatch` was already a persistent, manually/caller-populated workflow
object linking a Lead and Warehouse, optionally scoped to a Requirement. It has
`match_score` (0–100), `match_rank`, `capacity_fit`, `budget_fit`, textual
`requirement_compatibility`, `match_reasons`, `concern_reasons`, `top_reason`,
notes, provenance (`matched_by`, model ID/version), review fields and status.
There is no separate match-percentage or classification column. The score is
not a probability. Partial unique indexes permit one requirement/warehouse
record and one lead-level record per lead/warehouse pair.

The existing repository/services exposed CRUD and filtered saved-match lists,
but did not calculate suitability or generate candidates. The legacy warehouse
repository `get_available()` returns all stock despite its name; it is not used
by the new engine, and its legacy behavior is unchanged.

Phase 1 extends **the existing WarehouseMatch service, repository, schemas and
router**. A small rules module centralizes scoring policy. There is no second
orchestration service, duplicate matching model, new table, dependency or
migration. Existing historical migrations are untouched.

Relationships used by the domain:

- Requirement belongs to Lead; Lead belongs to Company.
- Company belongs to Organization; Organization can reference Industry.
- Warehouse belongs to a User (owner), not directly to Company/Industry.
- WarehouseMatch references Lead, optional Requirement, Warehouse and optional
  reviewing User; all existing relationships remain unchanged.

The warehouse model has total/built-up/open sqft, height, floor load,
city/state/country/pincode, coordinates, rent/month and currency, minimum lease,
availability status/date, occupancy rate and free-text amenities/certifications.
Requirements have minimum/maximum/built-up/open areas, preferred state/city/
locality/pincode, coordinates/radius, warehouse type, financial, technical,
operational, business and timeline fields. Only comparisons with sufficiently
clear Phase 1 semantics are scored below. The broader database design document
describes future concepts that are not all implemented in these models.

## Lifecycle and API

**GET `/warehouse-matches/requirements/{requirement_id}/recommendations?limit=100`**

There is **no `/api/v1` URL prefix**. The operation requires the existing active
authenticated user dependency; no new authorization model is introduced.

- Each request recalculates from current saved data; it is read-only.
- `limit`: integer 1–100, default 100, applied **after global ranking**.
- Missing requirement: `404`, `{"detail": "Requirement not found"}`.
- Invalid query/path types or limit: `422`; invalid/missing JWT or inactive user:
  `401` under existing authentication behavior.
- No eligible warehouses: `200` with an empty matches list.
- Draft/on-hold/closed/cancelled requirements may be evaluated for advisory use;
  a response-level warning identifies their non-ACTIVE status.
- Service callers must use a session without pending new/dirty/deleted objects;
  otherwise a `ValueError` prevents accidental flushes or unsaved-data scoring.

The response has requirement/lead IDs, `scoring_version: warehouse-rules-v1`,
candidate count, limit, ranked matches, and response-level limitations. Each
match has warehouse ID/name, rank, score, level, four factor reasons, explicit
score-cap adjustments, warnings, and optional `existing_match_id` and
`existing_match_status`.

Saved matches are **not silently created or updated**. Existing admin-only
POST/PUT/DELETE and authenticated saved-list/specific-match GET operations
remain intact. They are the existing explicit persistence/review workflow.
Fresh suitability and a saved score may legitimately differ. Existing rejected,
shortlisted, proposed, converted or other workflow decisions are surfaced, not
overwritten or used to fabricate physical suitability. A linked result includes
a warning to consult that saved decision. GET never assigns provenance or persists
results. There is no score history.
Dynamic recommendations do not change Lead Intelligence's saved-match inputs.

### Explicit generation and refresh

**POST `/warehouse-matches/requirements/{requirement_id}/generate`** requires
`get_current_admin`. No request body is required. The same operation generates
initial matches and refreshes them after warehouse/requirement edits. A missing
requirement returns 404; authentication failures return 401/403 as appropriate.
An integrity conflict rolls back the entire operation and returns 409 for retry.
The response contains requirement ID, scoring version, eligible candidates
evaluated, created/refreshed/stale/preserved counts, and limitations.

- Evaluates all eligible warehouses, without a first-100 cutoff. Low-scoring
  alternatives are saved with their penalties, not silently filtered out.
- Uses existing unique requirement/warehouse indexes; repeated runs update the
  same IDs. Legacy lead-only matches and other requirements remain untouched.
- New rows use the existing `AI_RECOMMENDED`/`AI` enum values for automated
  provenance, with `model_id=bwip-warehouse-rules` and version `warehouse-rules-v1`.
  These legacy enum names do **not** mean an LLM or ML model was used.
- Refresh only manages rows bearing this engine ID, `matched_by=AI`, no reviewer
  or review timestamp, and status AI_RECOMMENDED or STALE. Other engine, manual,
  hybrid, reviewed, rejected, shortlisted, proposed, chosen and converted rows
  are preserved entirely. Their stored scores can differ from live recommendations.
- Engine-managed rows whose warehouse becomes ineligible are re-evaluated with
  the ineligible cap (39), marked STALE, unranked, and given explicit concerns.
  If eligibility returns, the same row is refreshed/reactivated. Notes survive.
- Scores and explanations are refreshed together. `match_reasons` stores a JSON
  array of four factor objects; `concern_reasons` a JSON warning array including
  unsupported requirement criteria; `requirement_compatibility` a JSON object
  with scoring_version, match_level and adjustments. These remain **text columns**
  and strings in the existing API; legacy manually entered strings remain valid.
- Existing GET `/warehouse-matches/?requirement_id={id}&limit=100&offset=0`
  retrieves saved rows, including stale and preserved workflow rows, ordered by
  score descending, warehouse ID ascending, then match ID. Saved detail remains
  GET `/warehouse-matches/{match_id}`. Both add `match_level`, derived from the
  stored score; warehouse detail remains GET `/warehouses/{warehouse_id}`.
- Stored `match_rank` is one-based among currently eligible **engine-managed**
  rows only. Preserved manual ranks are not rewritten. Therefore mixed saved-list
  position need not equal match_rank; live recommendations rank current suitability.
- One transaction locks the requirement and existing match rows on PostgreSQL,
  serializing generation for the same requirement and protecting existing reviews.
  Unique indexes also guard competing manual inserts. Generation owns its commit/
  rollback and requires a clean session. SQLite tests do not validate row locking.
- Generation retains the eligible catalog plus existing matches in memory for
  persistence/ranking (O(N) memory, O(N log N) ranking). The bounded streaming
  guarantees below apply only to GET recommendations. Benchmark generation before
  large-catalog rollout. Concurrent warehouse edits may require another refresh;
  generation is not a vacancy reservation or an immutable inventory snapshot.
- Explicit POST changes the saved matches consumed by subsequent Lead Intelligence
  calculations; it does not rewrite existing lead snapshots or lead fields.

## Scoring policy

All weights, thresholds, caps, eligibility statuses and batch/result limits are
centralized in the warehouse matching rules module. Scores use integer points
and Decimal area comparisons; there is no randomness, wall-clock decay, network
lookup, fuzzy location comparison or external AI.

| Factor | Maximum | Rules and business meaning |
|---|---:|---|
| Location | 30 | Compare every nonblank preferred state/city/pincode with warehouse state/city/postal_code after whitespace/case normalization. All supplied preferences equal: 30. If not all match, matching city with no state conflict: 20; matching state: 10; otherwise 0. A conflicting state always gets 0. Pincode equality never overrides conflicting city/state. No supplied preferences: 0. |
| Capacity | 35 | Positive required_builtup_area and required_open_area must individually fit built_up_area_sqft and open_area_sqft; minimum_area compares to total_area_sqft. Known total must also meet combined component demand. Every check satisfied: 35. More than twice any requested checked area, or total above maximum_area: 25 with a subdivision/commercial-fit warning. Shortage, unknown required warehouse area, invalid input, or no positive area demand: 0. |
| Availability | 20 | AVAILABLE: 20. PARTIALLY_OCCUPIED: 10, with unverified vacancy warning/cap. Other/unknown status: 0 (excluded from candidate retrieval). available_from is not a date-compatibility score. |
| Type | 15 | Same specific WarehouseType enum: 15. Missing, OTHER, or different enum: 0. MULTIPURPOSE is not assumed interchangeable with other types. |

**Maximum total: 100.** Unknown or unspecified data earns no unverified points;
weights are not redistributed. A minimal requirement with only its required
identity/title fields scores 20 against AVAILABLE stock, not 100.

### Capacity details and assumptions

- Requirement area fields are interpreted as **square feet** to match warehouse
  column units; verify this convention against actual imported business data.
- Zero optional built-up/open demand means no demand for that component. Negative
  or nonfinite values are invalid. Explicit minimum/maximum bounds must be positive.
- Minimum above maximum or combined component demand above maximum is invalid.
- Missing or invalid warehouse dimensions do not count as zero/sufficient capacity.
- No fallback substitutes total or open area for missing built-up area.
- Maximum alone does not establish a required minimum, so earns no capacity points.
- If maximum is supplied but warehouse total is unknown, capacity earns zero.
- Oversized stock is retained as an alternative; subdivision is **not** assumed.
- Total/built-up/open areas are physical stock, not recorded vacant floor space.
  Occupancy rate is not multiplied by area to invent vacant component capacity.

### Safety caps and classification

The base score is the sum of the four factor points. Apply caps in stable factor
order; every cap has an explanation, a nonpositive point adjustment and its
threshold. Even a non-binding cap is recorded with zero adjustment.

| Condition | Final score at most |
|---|---:|
| Physical capacity shortage or invalid/contradictory requirement area | 39 |
| Ineligible/unknown warehouse status (pure single-pair evaluator) | 39 |
| Partially occupied; invalid/conflicting occupancy; known type mismatch | 59 |
| Supplied location mismatch/unverified location; requested type unknown/OTHER | 79 |

AVAILABLE status with positive occupancy, occupancy outside 0–100/nonfinite,
or 100% occupancy triggers the vacancy verification cap. Partial stock remains
at most PARTIAL even when physical capacity and all other criteria match.

| Level | Final score |
|---|---:|
| EXCELLENT | 80–100 |
| GOOD | 60–79 |
| PARTIAL | 40–59 |
| POOR | 0–39 |

Classification is derived from the final score; no classification column is added.
Generated compatibility JSON also records the classification at evaluation time.
**EXCELLENT means excellent against supported criteria, not confirmed complete
leasing suitability.** Unsupported mandatory requirements still require review.

## Explainability

Every result contains all four reasons, including zero-point reasons, with
`factor`, `points`, `maximum_points`, and an evidence-based `explanation`.
`sum(reasons.points) + sum(adjustments.points) == match_score`.

Warnings identify shortfalls, unknown capacity/type/location, excessive size,
partial occupancy/conflicts, unevaluated availability date, and saved workflow
decisions. Response-level warnings list supplied criteria that Phase 1 does not
evaluate and explicitly distinguish the score from confidence and verified
vacant capacity. No confidence score or completeness bonus is invented.

## Candidate selection and performance

The repository queries only AVAILABLE and PARTIALLY_OCCUPIED warehouses; unknown,
OCCUPIED, UNDER_MAINTENANCE and INACTIVE stock is excluded. Location/size/type
mismatches remain visible as scored alternatives with warnings.

One requirement SELECT plus one streamed warehouse SELECT (left joined to
existing requirement-scoped match ID/status) avoids N+1 access. SQLAlchemy
`raiseload("*")` blocks accidental warehouse relationship loading. The existing
unique requirement/warehouse index guarantees at most one joined workflow row.
JWT authentication adds its normal user lookup outside these two domain queries.

Candidates stream in batches of 200. A bounded heap retains only the best `limit`
results: O(N log limit) scoring/ranking work and O(batch + limit) retained matching
data. No implicit first-100 candidate truncation is used. All eligible candidates
must still be evaluated; benchmark this scan against production data volume.

Ranking is score **descending**, warehouse ID **ascending**; returned ranks are
one-based. Same saved database state and version give the same scores/order.
No stronger concurrent snapshot isolation than the existing session is promised.

## Limitations and deployment

- No industry suitability mapping exists on Warehouse despite the customer's
  Company → Organization → Industry context. No industry points are awarded.
- Locality is not compared to free-text addresses. No district field or GIS,
  distance/radius routing, alias/geocoding or geographic inference is used, even
  though optional coordinates exist.
- Per-sqft requirement budget vs monthly warehouse rent lacks an agreed rentable
  area/currency basis. Technical height/floor-load and lease criteria are deferred
  pending agreed unit/semantic rules. Amenities/compliance and other unmatched
  operational fields cannot be verified from free text.
- No wall-clock-dependent availability calculation, vacancy reservation,
  confidence metric, recommendation history, ML/LLM, external API or worker.
- Authentication/global authorization is unchanged; this is **not** tenant isolation.
- No schema changes: SQLite tests run with foreign keys enabled, but live
  PostgreSQL streaming/query behavior and representative real data still need
  deployment validation. No production database was contacted by this work.
- Existing Company ownership/backfill and previous migration deployment risks
  remain separate; feature completion is not approval of those migrations.
- Calibrate weights, oversize thresholds, type substitutions and area-unit
  assumptions with leasing users before broad production rollout.

## Verification

The feature tests cover minimal/excellent matches, all classification boundaries,
shortages, invalid/nonfinite and missing data, location normalization/conflicts,
all statuses/types, occupancy conflicts, deterministic ranking/ties, >200
candidates, bounded query counts, empty/missing requirements, fresh recalculation,
pending-session protection, unchanged saved workflow/relationships, real JWT/API
authorization and schema validation. Persisted-generation tests additionally cover
the full Industry → Organization → Company → Lead → Warehouse/Requirement API flow,
stable saved pagination, repeated generation, refresh, stale/reactivation, preservation
of manual/reviewed decisions, rollback, and admin authorization using real JWTs.
Warehouse CRUD regressions were added because
the requested warehouse test module did not previously exist. Existing domain and
Lead Intelligence tests remain unchanged.