# Deal Pipeline — Phase 1

## Scope and architecture

The configurable Deal pipeline supports warehouse leasing closure, not warehouse
operations, inventory, billing or ERP. FastAPI endpoints delegate to Deal and stage
services; repositories perform persistence using existing SQLAlchemy/Pydantic/JWT
patterns. No new dependency, external AI call or automatic transition is introduced.

The database design's Deal domain is a long-term blueprint, not the exact Phase 1
schema. This implementation retains its three table names, stage key/name/order
conventions and organization ownership. It deliberately adds a required Requirement
and optional selected WarehouseMatch instead of duplicating company/warehouse IDs.
It uses existing integer-ID conventions, OPEN/WON/LOST status, optional expected
revenue and a single closed_at/closed_reason pair. Probability, forecasting,
campaigns, ownership assignment, ABANDONED, UUIDs and dwell-time analytics are deferred.
History uses restrictive foreign keys rather than the blueprint's cascading deletion.

## Stage configuration

Stages belong to an Organization. Both stage_key and stage_order are unique within
that Organization; display names need not be unique. Keys are uppercase identifiers,
orders are nonnegative, and terminal stages require exactly one of is_won/is_lost.
Nonterminal stages have neither outcome flag. Ordering does not constrain movement:
an OPEN Deal may explicitly enter any active stage in its Organization.

An administrator must configure stages before creating Deals. The migration does
not seed tenant-specific configuration. The regression workflow configures:

| Order | Key | Outcome |
|---|---|---|
| 10 | QUALIFICATION | Nonterminal |
| 20 | REQUIREMENT_CONFIRMED | Nonterminal |
| 30 | WAREHOUSE_SHORTLISTED | Nonterminal |
| 40 | SITE_VISIT | Nonterminal |
| 50 | COMMERCIAL_DISCUSSION | Nonterminal |
| 60 | NEGOTIATION | Nonterminal |
| 70 | WON | Terminal, is_won=true |
| 80 | LOST | Terminal, is_lost=true |

Referenced stage keys/outcomes cannot change and referenced stages cannot be
deleted, including history-only references. Rename, description, ordering and
deactivation remain available. Historical display snapshots survive renaming.

## Deal and transition contract

- Creation requires deal_name, lead_id, requirement_id and an active nonterminal
  stage_id. Organization derives from the Lead's Company; the Requirement must
  belong to that Lead. Opportunity identity is not editable afterward.
- One OPEN Deal per Requirement is enforced by a PostgreSQL/SQLite partial unique
  index. A new Deal may be created after the previous one closes.
- Optional selected_warehouse_match_id must belong to the same Lead. Its
  Requirement must be null (a Lead-level match) or equal the Deal's Requirement.
  Selection rejects REJECTED, STALE and CONVERTED matches and warehouses other than
  AVAILABLE/PARTIALLY_OCCUPIED. Selection can be changed or cleared while OPEN.
- Generic updates allow commercial fields and match selection only. They cannot
  change stage, identity, status or closure metadata.
- Creation appends an initial history row. Explicit transitions atomically save
  the stage, stage_entered_at and history with actor/reason/UTC timestamp. Terminal
  flags determine WON/LOST, closed_at and closed_reason.
- A same-stage request is a no-op, including a retry after terminal closure. Other
  transitions and generic edits of closed Deals are rejected. No reopening API exists.
- WarehouseMatch status, Warehouse availability and Lead status are never changed
  automatically. Winning does not require a selected match. Eligibility is checked
  at selection, not again at closure; transitions recheck relationship compatibility.

## API

These are the actual registered paths (no additional /api/v1 prefix).

| Method | Path | Access |
|---|---|---|
| GET, POST | /deal-pipeline-stages/ | Authenticated read; admin create |
| GET, PUT, DELETE | /deal-pipeline-stages/{stage_id} | Authenticated read; admin writes |
| GET, POST | /deals/ | Authenticated read; admin create |
| GET, PUT | /deals/{deal_id} | Authenticated read; admin update |
| POST | /deals/{deal_id}/transition | Admin |
| GET | /deals/{deal_id}/history | Authenticated |

Transition body: `{"to_stage_id": 7, "change_reason": "Terms accepted"}` (use an
existing stage ID). There is no Deal deletion or history mutation endpoint.
Successful writes return HTTP 200, following existing API conventions. Missing
resources return 404, workflow conflicts 409 and invalid request fields 422.
JWT authentication and existing role checks return 401/403 as applicable.

Deal filters: stage_id, lead_id, organization_id, is_active (OPEN vs closed).
Stage filters: organization_id, is_active. All lists/history accept skip >= 0 and
limit 1–100 (default 100). Stages sort by organization/order/ID ascending; Deals
and history sort by creation/change timestamp then ID descending. Deal lists
eager-load stage in one SELECT to avoid per-item queries during serialization.

## Integrity and operational limits

Normal ORM updates/deletes of history are rejected; API history is read-only.
This is application-level append-only history, not a tamper-proof ledger: bulk
ORM operations, SQLAlchemy Core and direct SQL can bypass the mapper hooks. No
database trigger or database-role privilege policy is installed by this migration.

Source service guards reject deleting referenced Leads, Requirements, matches,
warehouses and companies, and reject supported source relationship reassignment.
CompanyUpdate already excludes organization changes; its legacy unknown-field
behavior ignores that input. Organization deletion retains the existing 409 handling
for references, including an Organization with only configured stages.

Deal writes lock relevant rows on PostgreSQL, roll back on failures, and reject
sessions with unrelated pending ORM changes. Services own commit/rollback and are
not composable inside a caller-owned transaction. SQLite does not implement the
same row locks. Existing source mutation guards are check-before-write operations:
concurrent reassignment/deletion races and lock ordering have not been proven safe.
The unique index protects duplicate OPEN Deals, but this is not a blanket guarantee
of cross-record consistency under concurrent or direct SQL writes. Deadlock retry
handling is not implemented. Live PostgreSQL concurrency testing is still required.

Organization compatibility is data validation, not tenant authorization. Existing
users/roles are global; organization filters do not establish a tenant security
boundary. Do not expose this as an isolated multi-tenant API without authorization work.

## Migration and verification

Revision j5b6c7d8e9f0 follows i4a5b6c7d8e9 and creates deal_pipeline_stages, deals and
deal_stage_history with indexes, checks and restrictive foreign keys. Downgrade
drops those three tables in dependency order and permanently removes pipeline data;
back up before any deployment rollback. No existing rows are backfilled or seeded.

Validation uses disposable FK-enabled SQLite and offline PostgreSQL DDL. Tests cover
JWT roles, the full leasing flow, terminal outcomes, boundaries, stage management,
duplicate prevention, pagination/order, historical snapshots, ORM immutability,
failure rollback/session recovery, source protections and migration round-trips.
The migration round-trip uses minimal parent tables, not a full live PostgreSQL
deployment migration. No production database was migrated or queried for validation.

Verified on 2026-09-09 after the final regression additions: the full application
suite passed **551 tests, 0 failures** (3,410 warnings). This includes 75 Deal workflow
and migration tests. The preceding affected-module regression run passed 334 tests;
these counts overlap and must not be added. Python syntax compilation passed for
129 application/test/migration files. Mapper configuration, OpenAPI generation
(69 operations), unique route/operation IDs, the single Alembic head and
`git diff --check` passed. Warnings remain unresolved; live PostgreSQL, production
migration execution and concurrency/load testing were not performed.

Run the application suite in PowerShell with isolated settings:

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
$env:SECRET_KEY='isolated-deal-validation-key-not-for-deployment'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHON_DOTENV_DISABLED='1'
& 'e:\BHOODEVI-Warehouse-Intelligence-Platform\.venv\Scripts\python.exe' -B -m pytest 'e:\BHOODEVI-Warehouse-Intelligence-Platform\tests' -q -p no:cacheprovider --disable-warnings
```