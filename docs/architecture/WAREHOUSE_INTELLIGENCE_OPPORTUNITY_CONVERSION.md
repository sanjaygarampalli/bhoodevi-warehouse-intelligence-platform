# Warehouse Intelligence → Opportunity Conversion

## Version 1 boundary

`WarehouseMatch` is the first and only supported persisted warehouse-intelligence source. It already provides traceable Lead, optional Requirement, and Warehouse identity and is validated by the existing Deal rules.

The canonical workflow is:

```text
WarehouseMatch → WarehouseIntelligenceOpportunityConversion → Deal
```

The conversion record is the audit boundary: organization, source classification, initiating user, lifecycle status, timestamps, and resulting Deal are persisted. A unique source foreign key makes retries idempotent.

Conversion uses the existing `DealService` validation path and a transaction-aware handoff. The source determines Lead and Warehouse; callers supply only explicit Deal commercial fields and a same-organization pipeline stage.

## Lifecycle and tenant safety

Records use `PENDING`, `CONVERTED`, `REJECTED`, and `FAILED`. Version 1 creates `PENDING` and atomically completes it as `CONVERTED`; rejected or technical failure paths do not leave a converted record or Deal. Organization write access is checked using active organization membership, and source/stage ownership is validated by the Deal domain.

## Pilot is intentionally deferred

Warehouse Pilot output is currently calculated on demand and has no persisted assessment identity. This milestone does **not** fake a Pilot foreign key, serialize an ephemeral result, or modify protected Module 3 files.

Future path:

```text
Warehouse Pilot Profiles
→ Persisted Warehouse Pilot Assessment
→ Warehouse Intelligence Opportunity Conversion
→ Deal
```

That future assessment must provide its own identity, organization, company, warehouse, version/snapshot, classification, blockers, evaluator, and evaluation timestamp before Pilot-to-Deal conversion can be safely enabled.