# Action & Follow-up Intelligence Engine

## Purpose

The Action Intelligence Engine converts BWIP's existing read-only intelligence
into a bounded, explainable queue answering: **what should the business do next?**
It does not persist recommendations, change lead/deal state, or introduce a new
lead-scoring model.

## Architecture and data sources

`ActionIntelligenceService` orchestrates `ProspectPrioritizationService`, lead
intelligence, open follow-up tasks, open deals, saved warehouse matches, lead
activity freshness, decision makers, companies, and requirements. All responses
use Pydantic schemas; no migration or new table is required.

## Action generation and priority

The service emits at most one action for each active lead. The precedence is:

1. `FOLLOW_UP_OVERDUE`
2. `DEAL_AT_RISK`
3. `REVIEW_HIGH_MATCH`
4. `CONTACT_DECISION_MAKER`
5. `FOLLOW_UP`
6. `REENGAGE_COLD_LEAD`
7. `REVIEW_REQUIREMENT`
8. `CONTACT_LEAD`

Existing `PriorityLevel` values are reused. Lead priority comes from the
canonical prioritization result; overdue interventions are promoted to
`CRITICAL`, while high matches and untouched decision makers are `HIGH`.

## Follow-up and stale-lead intelligence

Only `OPEN` and `IN_PROGRESS` tasks are actionable. A task before the evaluation
clock is overdue. An active lead is stale when it has no active follow-up and has
no `last_activity_at` or has not been active for `STALE_LEAD_DAYS` (currently 30
days). This threshold is dynamic recommendation policy, not a new Lead status.

## Deal and warehouse handling

An open deal is at risk only when its persisted `expected_close_date` is before
the current UTC date. No revenue forecast is invented. Warehouse recommendations
reuse the existing `HIGH_MATCH_SCORE` policy and exclude rejected or stale saved
matches.

## API

All endpoints require the existing JWT `get_current_user` dependency:

- `GET /action-intelligence/summary`
- `GET /action-intelligence/actions?priority=HIGH&action_type=FOLLOW_UP&limit=20`
- `GET /action-intelligence/today?limit=20`
- `GET /action-intelligence/leads/{lead_id}?limit=20`

The queue is computed dynamically and limits are bounded by query validation.

## Dashboard integration

The operational dashboard exposes only summary-level action counts in its
executive summary: `critical_actions`, `overdue_actions`, and `todays_actions`.
The detailed queue remains the source of truth at the Action Intelligence API.

## Limitations and future improvements

The implementation favors reuse and correctness over a materialized queue.
Organization-level authorization still depends on a future user-to-organization
access model. Future work can add tenant scoping, richer completed-follow-up
chaining, aggregate SQL for very large datasets, and explicit deal risk fields.