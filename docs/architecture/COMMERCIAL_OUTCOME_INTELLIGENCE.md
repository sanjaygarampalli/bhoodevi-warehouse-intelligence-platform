# Commercial Outcome Intelligence (Module 6)

## Purpose

Module 6 closes the feedback loop from real leasing execution to future business
prioritization. It records only explicitly supplied Deal outcome evidence and
derives historical aggregates from the existing Deal, Lead, Company, and selected
WarehouseMatch records.

## Canonical workflow

`Intelligence -> Company -> Candidate -> Conversion -> Lead -> Requirement -> Warehouse Match -> Deal -> Activities/Tasks -> canonical Deal transition -> WON/LOST -> structured outcome -> historical analysis`

The existing `POST /deals/{id}/transition` workflow remains authoritative. A
terminal pipeline stage sets `deal_status`, `closed_at`, and the existing
`closed_reason`. New outcome fields are nullable and are never inferred or
backfilled.

## Outcome semantics

`WON` means a commercially won Deal according to the configured pipeline stage;
it does not claim that a legally executed lease exists. Explicit final amount,
currency, lease duration, notes, and evidence reference may be captured at the
terminal transition. Lost Deals may carry a bounded category plus free-text
closure reason. Older or incompletely recorded losses remain `UNKNOWN` in
analytics rather than being guessed.

## Analytics

`GET /commercial-intelligence/outcomes/summary?organization_id=...` reports
closed Deals, Won/Lost counts, closed-deal win rate, lost-reason counts, and
historical associations by company industry, lead source, and selected warehouse
match. Every group includes its sample size. Empty data returns zero counts and
empty groups; win rate is `null` when there are no closed Deals.

This is historical descriptive analysis, not prediction or causal attribution.
Warehouse Pilot classifications and MarketSignal provenance are intentionally
not reported because the current persisted relationships do not trace them
reliably to a Deal.

## Security and deferred scope

The endpoint requires authentication and validates organization membership using
the canonical organization access helper. No caller may read another
organization's Deal outcomes through this endpoint. Contract/lease execution,
revenue recognition, forecasting, AI learning entities, and predictive win
probabilities are deferred until the repository has trustworthy supporting data.