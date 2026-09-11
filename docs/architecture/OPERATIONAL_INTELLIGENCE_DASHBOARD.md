# Operational Intelligence Dashboard

## Purpose

`GET /operational-dashboard` is BWIP's read-only operational view for deciding what the business team should act on today. It aggregates existing lead intelligence, prospect prioritization, follow-up work, deal pipeline state, warehouse matches, requirements, and recorded lead activity.

## Architecture

The API delegates to `OperationalDashboardService`. The service composes `ProspectPrioritizationService` for canonical lead/opportunity priority scores and next-best actions. It does not write snapshots, alter workflow state, or implement a second scoring engine.

## Sections

- **Executive summary:** active leads, priority bands, follow-up queues, open deals, overdue expected close dates, new leads, and strong matches.
- **Today's attention:** overdue/due-today open tasks plus actionable critical/high priority leads and opportunities.
- **Pipeline summary:** deals grouped by the configured `DealPipelineStage`, including active/total counts and expected revenue.
- **Lead health:** intelligence bands, recent/inactive activity, missing decision makers/requirements, and qualification needs.
- **Warehouse opportunities:** existing viable/strong `WarehouseMatch` records and active requirements without a non-rejected/non-stale match.
- **Top priorities:** a bounded ranking from the existing Prospect Prioritization Engine.
- **Recent activity:** the latest persisted `LeadActivity` rows; no activity is fabricated.

## API

`GET /operational-dashboard?top_priorities_limit=5&recent_activity_limit=10`

The endpoint requires the existing JWT `get_current_user` dependency. Both limits are bounded by query validation.

## Operational definitions

- Active leads exclude WON, LOST, and DISQUALIFIED.
- Strong matches use the existing `HIGH_MATCH_SCORE` policy; viable matches use the existing `VIABLE_MATCH_SCORE` policy.
- A deal is shown as at risk only when it is open and its persisted expected close date is before the current UTC date.
- Recent lead activity means activity within the previous 30 days. This is a dashboard freshness indicator, not a new intelligence score.

## Limitations

The dashboard is computed on request and does not persist snapshots or historical dashboard values. It currently aggregates the current database tenant scope; organization-level filtering can be added when the surrounding authorization policy is formalized. Deal-stage risk is intentionally conservative because the current model has no explicit risk field. Large datasets should eventually use aggregate SQL queries or a materialized operational read model; the current implementation favors reuse and clarity.
