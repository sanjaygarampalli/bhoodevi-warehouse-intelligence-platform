# Follow-up Tasks — Phase 1

## Purpose

Turn a recommended Next Best Action into an assigned, schedulable, trackable work item
so the business can manage **who** does it, **what**, **when** it is due, and **whether**
it was completed. This moves BWIP from recommending the next step to operating it.

## Domain

New model `FollowUpTask` (table `follow_up_tasks`) is a distinct, minimal work-queue
domain. It deliberately **does not duplicate** `LeadActivity`:

- `LeadActivity` records an **interaction that happened** (channel, outcome, duration)
  and may carry a `next_followup_date` as a free-form plan.
- `FollowUpTask` represents an **assigned piece of work with a due date and lifecycle**.

Completing a `FollowUpTask` does **not** automatically create a `LeadActivity`, because
finishing a task (e.g. research, internal review) is not proof that an outreach
interaction occurred.

## Fields

- `lead_id` (required), `deal_id` (optional), `assigned_to_user_id` (optional)
- `subject`, `description`
- `task_type`: `CALL, EMAIL, LINKEDIN, WHATSAPP, MEETING, PROPOSAL_FOLLOWUP, REVIEW, ADMIN, OTHER`
  (aligned with the `follow_up_tasks` blueprint in `DATABASE_DESIGN.md`)
- `priority`: reuses `LeadPriority` (`LOW, MEDIUM, HIGH, URGENT`)
- `status`: `OPEN, IN_PROGRESS, COMPLETED, CANCELLED`
- `due_at`, `completed_at`, `cancelled_at` (timezone-aware UTC)
- `recommendation_key`, `recommendation_context` (explainable Next Action provenance)

## Lifecycle and Overdue

- Transitions: `OPEN → IN_PROGRESS → COMPLETED` or `→ CANCELLED`. Terminal tasks are
  immutable through the service (no re-open, no outcome swap).
- **OVERDUE is never a stored status.** It is computed on read as
  `status in (OPEN, IN_PROGRESS) and due_at < now(UTC)`. Completed/cancelled tasks are
  never overdue.
- Completion sets `COMPLETED` + `completed_at`; cancellation sets `CANCELLED` +
  `cancelled_at`. Retrying a terminal transition with a conflicting note fails clearly.
- A CHECK constraint guarantees the `status`/`completed_at`/`cancelled_at` invariant at
  the database level.

## Data Integrity (service layer)

The service validates: Lead exists; optional Deal exists and belongs to that Lead and the
Lead's organization; optional assignee exists and is active; a Deal/Lead mismatch is
rejected. `completed_at` is managed only by the completion workflow. Source-record
reference guards block deleting/reassigning a Lead, Company, or assigned User that is
still referenced by a task, preserving history.

## Next Best Action Integration

`POST /leads/{lead_id}/next-action/task` explicitly evaluates the **current** Lead
Intelligence, reads the recommended action and reason, and creates a `REVIEW` task that
preserves the full recommendation context (action, reason, missing information,
limitations, scoring version, total score, calculated_at).

- `MONITOR` produces **no** task (no outreach is recommended).
- A partial unique index `uq_follow_up_tasks__active_recommendation`
  (`lead_id, recommendation_key` where the task is active and `recommendation_key` is
  set) prevents duplicate active tasks for the same recommendation. Retrying returns the
  existing task without changing its deadline, assignee, or evidence. After a task is
  terminal, a fresh recommendation can be scheduled again.
- No background job runs this; it is only ever triggered by the explicit operation.

## Deal Integration

A task may reference a Deal (e.g. site-visit preparation, negotiation follow-up). Deal
association is optional and its consistency with the Lead and organization is validated.

## Operational Queues

`GET /follow-up-tasks/` supports filters `lead_id`, `deal_id`, `assigned_to_user_id`,
`status`, and operational `queue` values `OPEN`, `OVERDUE`, `UPCOMING`. Ordering is
deterministic: overdue first, then `due_at`, then priority (`URGENT>HIGH>MEDIUM>LOW`),
then `id`. Listing is a single query with relationships disabled (`raiseload`) to avoid
N+1; the overdue flag is computed in-process.

## Authentication / Authorization

Reads require any authenticated user; writes (create, update, complete, cancel, and
Next-Action task creation) require admin, matching the existing Deal/Led/Company write
pattern. Organization compatibility is **data validation, not tenant authorization**.

## Migration

Single forward-only migration `k6c7d8e9f0a1_add_follow_up_tasks` (head, after
`j5b6c7d8e9f0`). It creates one table with the FKs, four operational indexes, the
closure CHECK constraints, and the partial unique recommendation index. `downgrade()`
drops the table (destructive to task history); it is not run against production.

## Verification (2026-09-09)

Validated against isolated in-memory SQLite with foreign keys enforced and a
deterministic clock: 61 focused Follow-up tests, PostgreSQL DDL/model parity and
upgrade/downgrade/constraint tests for the migration, and a full-suite regression of 612
passed. Not validated against live PostgreSQL concurrency or production data.

## Operational Limits

- Users have no organization membership, so assignment cannot enforce tenant-level
  assignment authorization.
- History/source-record protection applies through the service and ORM guards; direct
  SQL or bulk operations can bypass it.
- Concurrency (duplicate active-recommendation races, lock ordering, deadlock retry) is
  handled by the partial unique index and rollback of pending-change workflows but is not
  validated under live multi-writer load.