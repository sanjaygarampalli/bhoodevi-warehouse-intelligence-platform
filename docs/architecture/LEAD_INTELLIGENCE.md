# Lead Intelligence — Phases 1 and 2

## Architecture and contract

FastAPI Lead endpoints delegate to `LeadIntelligenceService`. `LeadRepository`
loads the lead/company/owning organization in one query, then select-in loads
company contacts, requirements, activities and matches (with warehouses): five
SELECTs for a populated lead, without collection cartesian products or per-row
lazy queries. History is a separate bounded query and is never loaded to score.

`evaluate_lead` is a pure evaluator of that loaded graph with an explicit
calculation timestamp. The service supplies UTC time, but scoring never reads
the clock. Identical saved inputs and scoring version produce identical scores,
priorities and reasons. Only the calculation timestamp changes. Phase 1 does not
apply recency decay: old recorded engagement is not represented as recent.

Company has a mandatory owning Organization (`organization_owners`). Its
`industry` is free text; the owning Organization's Industry describes the tenant,
not necessarily the prospect. Industry presence earns completeness points only;
there is no unsupported relevance or verification claim.

## v1 scoring (maximum 100)

Policy is centralized in `app/services/lead_scoring_rules.py`: version, weights,
priority boundaries, match thresholds and meaningful activity types. Eligibility
is implemented in `app/services/lead_intelligence.py`. Any policy/eligibility
change that changes a score must increment `SCORING_VERSION` before deployment.

| Category | Subfactors | Maximum |
|---|---|---:|
| Company | Associated 5; owning Organization 3; industry recorded 2; legal name 2; website 3; headquarters city AND state 3; products 2 | 20 |
| DecisionMaker | Named, non-disqualified company contact 5; designation AND recognized decision level 3; email recorded 5; phone recorded 5; at least two contactable company contacts 2 | 20 |
| Requirement | ACTIVE 5; positive area with nonnegative, consistent bounds 8; city OR pincode 6; IMMEDIATE or 1_3_MONTHS move-in 5; positive budget_per_sqft 4; warehouse type AND goods/storage type 2 | 30 |
| Activity | Completed activity 3; completed outreach/meeting/proposal 5; latest such activity has INTERESTED/CALLBACK_SCHEDULED outcome 4; non-cancelled activity has follow-up after its activity date 3 | 15 |
| WarehouseMatch | Eligible match >=50 for available/partially occupied warehouse 5; one >=80 7; at least two distinct viable warehouses 3 | 15 |

One best contact and one best ACTIVE requirement are evaluated independently;
partial rows are not combined into a fictitious complete profile. Ties choose
the lowest database ID. Reasons identify the chosen contact/requirement. Contacts
from another company, including a mismatched primary contact, do not score.
Designation is supported by DecisionLevel other than OTHER, not guessed from a
job title. Contact details are recorded information, not verified information.

Meaningful activity types: CALL, EMAIL, LINKEDIN, WHATSAPP, MEETING, PROPOSAL.
Latest is ordered by activity_date then ID. A later negative outcome removes the
positive-outcome bonus; scheduled/cancelled activities do not imply engagement.
Follow-up points indicate recorded planning, not that a follow-up is still due.

Eligible match statuses: AI_RECOMMENDED, SHORTLISTED, PROPOSED, LEAD_CHOSEN.
REJECTED, STALE and CONVERTED do not score. Requirement-level matches must reference
an ACTIVE requirement belonging to this lead. Lead-level matches need no
requirement. Repeated matches to one warehouse do not count as multiple options.
Unknown or unavailable warehouse availability earns no match points.

Blank/whitespace profile fields do not score. Each of the 25 subfactors returns
`factor`, `points`, `max_points`, and `reason`, including missing evidence/zero
points. Total is bounded to 0–100. A valid minimal lead with its required Company
and Organization normally scores 10, not zero.

## Priority, not pipeline status

Reuse the existing `LeadPriority`; do not add a competing HOT/WARM/COLD enum:

| Score | Recommended priority | Conceptual band |
|---|---|---|
| 75–100 | URGENT | HOT |
| 50–74 | HIGH | WARM |
| 25–49 | MEDIUM | COLD |
| 0–24 | LOW | UNQUALIFIED |

These are recommendations in intelligence responses/snapshots. The engine never
overwrites `Lead.priority`, `Lead.status`, `Lead.ai_score`, or audit timestamps.
Pipeline status is independent: this is evidence quality, not win probability or
an instruction to reopen a closed lead. Consumers should apply pipeline status
filters when prioritizing acquisition work.

## API

The existing application has no `/api/v1` URL prefix despite its source layout.

| Method/path | Permission | Behavior |
|---|---|---|
| POST `/leads/{lead_id}/intelligence/calculate` | Active admin | Fresh calculation plus one appended snapshot; 200 |
| GET `/leads/{lead_id}/intelligence` | Active authenticated user | Fresh calculation, no persistence; 200 |
| GET `/leads/{lead_id}/intelligence/history` | Active authenticated user | Snapshot list, newest calculated_at then ID first; 200 |

POST takes no body and always persists (repeated calls intentionally append).
History uses `limit` (1–100, default 100) and `offset` (>=0, default 0). Empty
history is `[]`; a missing Lead is 404 on all three endpoints. Invalid pagination
is 422. Missing/invalid/expired/inactive credentials are 401; non-admin POST is
403. Responses expose lead_id, total_score, priority, scoring_version, reasons,
and calculated_at (UTC), not internal snapshot IDs.

## Persistence and migration

Discovery found only stale `lead_score_snapshot.cpython-312.pyc` containing a
former broader model. There was no source, registered metadata, migration or
tracked implementation. The new `LeadScoreSnapshot` implements this same table
concept, not a second score-history system. Broader next-generation database
design fields remain future scope rather than being assumed present.

Revision `i4a5b6c7d8e9`, after `h3f4e5d6c7b8`, creates only
`lead_score_snapshots`: integer ID, lead FK, bounded integer total_score,
existing leadpriority enum, scoring_version, structured reasons, and UTC
calculated_at. JSON uses the existing JSON-with-PostgreSQL-JSONB-variant pattern.
The shared leadpriority enum is neither created nor dropped by this revision.
An index on (lead_id, calculated_at, id) supports stable history pagination.

Snapshots are append/read-only through the service/API: historical reasons and
versions are not recomputed. There is no update endpoint. Direct database writers
can still alter rows; this is not a tamper-proof audit ledger. Deleting a Lead
cascades its snapshots. Downgrade drops this history table and index only and
therefore loses score history; take an appropriate backup first.

Persistence follows repository-owned commits. Use a clean request session;
snapshot creation rejects pending changes to avoid committing unrelated work.
Evaluation uses no-autoflush and does not mutate ORM entities.

## Validation and production considerations

Tests use the existing pytest/SQLAlchemy SQLite approach with foreign keys
enabled and FastAPI TestClient. API tests override only the DB session and exercise
real JWT decoding, active-user checks and admin authorization. Migration tests
exercise this new revision on empty/populated disposable SQLite parents and
compile PostgreSQL upgrade/downgrade DDL without contacting a live server.

Live PostgreSQL migration validation and deployment backup/rollback rehearsal
remain required. Inspect deployed schema/Alembic version for unmanaged legacy
snapshot tables before upgrade; stale local bytecode cannot establish live DB
state. The pre-existing Company organization ownership/backfill migration risk
is unchanged. Existing Lead authorization is global authenticated read/admin
write; tenant isolation/RLS is not introduced by this feature.

Concurrent edits between eager-load queries follow the existing database
transaction isolation. Strict point-in-time multi-query consistency would need
a reviewed isolation policy. Offset history pagination may shift under concurrent
inserts. Large lead collections still load into memory; batch/aggregate scoring
and cursor pagination can be introduced when measured workloads justify them.

Future candidates: calibrated relevance and weights, explicit as-of recency
policies, verified contacts, automatic recalculation, retention policy and richer
signals. No external AI calls or new dependencies exist in v1.

## Phase 2: explainable actions and live prioritized pipeline

Phase 2 reuses the existing evaluator, 25 scoring factors, priority enum,
snapshot table, repositories and authenticated Lead router. Score policy remains
`v1`: no weights, eligibility rules, manual Lead fields or WarehouseMatch behavior
are changed. `URGENT` is the established equivalent of HOT; research needs are
represented separately, not by adding a conflicting database priority enum.

### Additive response fields

All current, calculate and history responses include:

- `component_scores`: category -> `{score, max_score}`, aggregated exclusively
  from the response's stored factor points, including for historical versions.
- `positive_signals`: awarded factor explanations.
- `scoring_gaps`: unearned bonuses. These are not necessarily unknown data:
  FLEXIBLE move-in loses urgency points but is not a missing timeline.
- `explanation`: versioned action context, or null for old snapshots without
  recorded context. Includes `recommended_action`, `action_reason`,
  `research_required`, actual `missing_information`, limitations, selected
  contact/requirement IDs and the best eligible saved warehouse match evidence.

The best match uses score descending, then match ID ascending. Its stored status,
requirement ID, model version, compatibility text and positive/concern text are
copied as evidence, not parsed into a new suitability score. A match may belong
to another active requirement of this same lead, or be lead-level; the returned
IDs make that distinction visible. The existing warehouse engine does not prove
technical/compliance/timeline compatibility. Contact status QUALIFIED likewise
does not prove contact verification. These limitations are explicit in context.

### Action policy v1

Precedence is deterministic and based on stored facts, not clock-based recency:

1. WON, LOST, DISQUALIFIED or DORMANT -> MONITOR, never reopen automatically.
2. Latest completed meaningful activity NOT_INTERESTED -> MONITOR, even if an
   older follow-up plan exists.
3. Missing company/industry -> RESEARCH_COMPANY.
4. No named eligible company contact -> FIND_DECISION_MAKER.
5. Latest completed meaningful activity BOUNCED, or selected contact lacks
   email/phone or a recognized role -> RESEARCH_CONTACT.
6. No active requirement with valid size and city/pincode -> REVIEW_REQUIREMENT.
7. No eligible saved match -> FIND_WAREHOUSE_MATCH.
8. Positive latest engagement or recorded follow-up plan -> FOLLOW_UP. This is
   not a claim that the follow-up is due now.
9. Other completed meaningful outreach without a positive outcome/plan -> MONITOR.
10. Otherwise -> CONTACT_DECISION_MAKER; recorded details remain unverified.

Research is required for the company/contact/review-requirement actions. Action
recommendations do not modify score priority, pipeline status, contacts or matches.
Policy changes should increment `action_version` separately from score policy.

### Snapshot compatibility

New evaluations attach one typed `context` object to the `company.associated`
reason in the existing JSON reasons list. This is non-scoring evidence: the
25-factor contract and sum remain intact. Other reasons have null context.
The response exposes that stored object as `explanation` for convenience.
No new table, column or migration is required. Old reason JSON validates with
null context; no historical action is invented from today's data. Each calculate
POST still appends a snapshot. History reads never rewrite JSON or recalculate
historical reasons, actions or match evidence. Existing direct-writer and
lead-deletion limitations described above remain unchanged.

### GET /leads/prioritized

Requires the existing active authenticated user dependency (including non-admin
readers). No snapshot writes and no side effects. Registered before the numeric
Lead route to avoid path capture. Response: `{items, total, limit, offset,
calculated_at}`. Each item contains lead number/ID, company name/ID, organization,
industry, pipeline status and full current intelligence.

Filters:

| Parameter | Semantics |
|---|---|
| priority | Existing LOW, MEDIUM, HIGH, URGENT intelligence priority; not manual priority |
| minimum_score | Inclusive 0–100; default 0 |
| industry | Exact, case-sensitive Company.industry; 1–100 characters |
| organization_id | Positive owning organization ID; filter only, not tenant authorization |
| has_active_requirement | True/false for existence of an ACTIVE requirement |
| status | Exact LeadStatus; omitted excludes WON, LOST and DISQUALIFIED |
| research_required | True/false for the action-context research flag |
| limit | 1–100; default 100 |
| offset | 0–10000; default 0 |

All filters combine with AND. Unknown organization/industry returns an empty
page; invalid filter values return 422. Closed leads remain accessible via an
explicit status filter, with MONITOR actions. DORMANT is included by default
but also receives MONITOR. Sort order is priority descending, score descending,
lead ID ascending; ties and repeated unchanged reads are stable. A single UTC
calculation timestamp is shared across a response. Stored snapshots are never
used as a potentially stale current score cache.

Repository filters run in SQL, then keyset batches of 100 eagerly load the same
graph as single-lead evaluation (normally five SELECTs per populated batch).
Scoring filters run before pagination. A bounded top-k heap retains at most
offset + limit items, so sorting is not performed separately within each page.
`total` is the count after all filters. This still evaluates every SQL-filtered
candidate on every request: CPU is linear in the candidate graph, and large
collections per lead remain a memory consideration. Measure production workload
before deciding on a materialized scoring cache/background job. Deep offsets
are capped. Concurrent data changes can move items between pages; this is not a
transactionally frozen cursor or snapshot-isolated multi-query export.

### Phase 2 validation scope

Tests extend existing fixtures and real JWT/TestClient coverage: action paths,
all existing priority boundaries, component arithmetic, missing-vs-nonurgent
timeline, legacy snapshots, unchanged history evidence, live ranking, heap
replacement across batches, deterministic ties, pagination, combined filters,
closed pipeline status, authentication, and route resolution. Local SQLite
regressions do not establish live PostgreSQL production readiness. PostgreSQL
migration rehearsal, transaction isolation review, and production-scale pipeline
latency/memory checks remain required.

### Inspection inventory for this increment

Inspected source files or relevant source ranges (workspace absolute paths):

```text
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\lead.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\lead_score_snapshot.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\company.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\organization.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\decision_maker.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\requirement.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\warehouse_match.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\lead_activity.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\repositories\lead.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\repositories\lead_score_snapshot.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\repositories\decision_maker.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\repositories\requirement.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\repositories\warehouse_match.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\services\lead.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\services\lead_intelligence.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\services\lead_scoring_rules.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\services\warehouse_match.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\schemas\lead.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\schemas\lead_intelligence.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\api\v1\endpoints\lead.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\api\v1\routes.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\dependencies.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\dependencies_admin.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\core\config.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\main.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_lead.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_lead_intelligence.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_lead_intelligence_migration.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_integration_audit.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_warehouse_matching_intelligence.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\alembic\versions\i4a5b6c7d8e9_add_lead_score_snapshots.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\docs\architecture\LEAD_INTELLIGENCE.md
```

The migrations directory and working-tree status were also inspected. Existing
uncommitted warehouse intelligence and other unrelated changes were preserved.

## Snapshot/history completion audit (2026-09-09)

The continuation audit found the snapshot model, repository, service workflow,
response schema, authenticated routes and revision `i4a5b6c7d8e9` already present.
They are reused without rewriting the scoring policy or adding parallel routes.
The snapshot model already imports `Lead` inside `if TYPE_CHECKING` and uses a
string relationship target. This resolves the reported undefined-name annotation
without a circular runtime import or any database schema change.

The supported calculation workflow supplies `SCORING_VERSION = "v1"` explicitly
to every result and snapshot. This is the service-level default, not a database
default: direct ORM/SQL writers must supply the actual version rather than
silently labeling arbitrary historical data as today's policy. Future scoring
changes must increment the version; history reads stored versions, points,
maximum points, reason text and action context without consulting current rules.
Component totals are derived from those stored factors, not duplicated columns.

Repeated GETs never create history. The existing admin-only calculate POST is an
explicit append command, including when inputs have not changed; preserving that
contract permits intentional observations at distinct times. Clients should use
GET for polling and must not treat POST retries as idempotent. No automatic
snapshotting, deduplication guarantee or retention policy is introduced here.

History reproduces saved results and their explanations, not a complete replay
of the original database graph. Selected contact/requirement IDs and saved match
evidence are retained, but entire company/contact records and all scoring inputs
are not copied. Source edits cannot rewrite saved factors; source IDs alone do
not recover deleted or edited raw records. Snapshots remain application-level
append-only records, not a tamper-proof or perpetual audit ledger.

Additional regression coverage verifies fresh-interpreter imports and reciprocal
mappers, database relationship round-trips, all 25 persisted factors, historical
independence from current policy, service missing-lead/pagination handling,
failed-insert recovery, and repeated API reads versus explicit appends. No new
migration or endpoint is required for this completion audit.

Verified locally after the audit: focused intelligence/migration tests **127
passed**; combined 12-module Lead/company/contact/requirement/warehouse and
integration regression suite **363 passed, 0 failed**, with **2,617 warnings**,
all `datetime.utcnow()` deprecations. The combined count includes the focused
tests. Python compilation passed for all 58 modified/untracked Python files under
the application, tests and Alembic directories. Model imports, mapper resolution,
OpenAPI generation, Lead route uniqueness and the single Alembic head passed.
The database tests use disposable SQLite; PostgreSQL coverage is offline DDL
only. Live PostgreSQL, full deployment migrations, concurrent transactions,
production-volume benchmarks and the VS Code Pylance UI were not tested.

In addition to the core inventory above, the continuation inspected relevant
ranges in these files:

```text
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\models\__init__.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\services\company.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\services\decision_maker.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\services\requirement.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\schemas\company.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\schemas\decision_maker.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\schemas\requirement.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\schemas\warehouse_match.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\api\v1\endpoints\company.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\api\v1\endpoints\decision_maker.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\api\v1\endpoints\requirement.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\app\api\v1\endpoints\warehouse_match.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_company.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_decision_maker.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_requirement.py
e:\BHOODEVI-Warehouse-Intelligence-Platform\tests\test_warehouse_match.py
```