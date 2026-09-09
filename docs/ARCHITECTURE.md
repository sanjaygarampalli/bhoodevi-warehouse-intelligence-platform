# Architecture

## Current Backend Stack

- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic v2
- JWT authentication
- Role Based Access Control

## Development Rule

This is an existing backend application. Do not generate a new project scaffold or rebuild working modules without a genuine architectural reason.

## Layer Order

Inspect and evolve the system in this order:

1. Folder structure
2. Database layer
3. Models
4. Schemas
5. CRUD
6. Services
7. API
8. Authentication
9. Business workflow
10. AI modules

## Backend Layering

API routes should validate requests and delegate business behavior to services.

Services should hold business workflow logic.

CRUD modules should perform database access only.

Models and migrations should remain normalized and backward compatible whenever possible.

## Lead Intelligence — Phase 1

The implemented rule-based scoring engine is described in
[Lead Intelligence](architecture/LEAD_INTELLIGENCE.md). It uses existing Lead
relationships, reuses LeadPriority, and stores explainable, versioned snapshots
without changing the Lead's manually managed fields or calling external AI APIs.

## Warehouse Matching Intelligence — Phase 1

[Warehouse Matching Intelligence](architecture/WAREHOUSE_MATCHING_INTELLIGENCE.md)
documents the deterministic requirement-to-warehouse recommendation engine. It
extends the existing WarehouseMatch module with fresh ranked, explainable results
and status-filtered candidates, while preserving saved manual/review workflows.
An explicit admin-only generation/refresh operation persists engine-managed scores
and explanations in existing WarehouseMatch columns; read-only recommendations
remain non-mutating. Manual/reviewed decisions are not overwritten.
No new table, migration, external AI dependency or tenant architecture is introduced.

## Deal Pipeline — Phase 1

[Deal Pipeline](architecture/DEAL_PIPELINE.md) documents configurable organization
stages, Lead/Requirement-linked Deals, optional WarehouseMatch selection, explicit
transitions and application-level append-only history. It describes the migration,
API contracts, design differences from the long-term database blueprint, and the
limits of history immutability, concurrency and organization authorization.

## Follow-up Tasks — Phase 1

[Follow-up Tasks](architecture/FOLLOW_UP_TASKS.md) documents the assigned work-queue
domain that turns a recommended Next Best Action into a tracked Follow-up Task with a
due date, assignment and OPEN/IN_PROGRESS/COMPLETED/CANCELLED lifecycle. Overdue is
computed dynamically, Lead/Deal consistency is validated in the service, and a partial
unique index prevents duplicate active tasks per recommendation. It complements, and does
not duplicate, the existing LeadActivity interaction record.
