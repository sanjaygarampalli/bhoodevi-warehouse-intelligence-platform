# Canonical Persisted Warehouse Pilot Assessment

## Purpose

The existing Warehouse Pilot endpoint evaluates suitability and returns a composite result, but the result was previously transient. `WarehousePilotAssessment` is the historical business decision created by the explicit evaluate-and-persist workflow.

`WarehouseRequirementAssessment` remains an input/profile component. It is not the final Pilot decision.

## Workflows

The existing `POST /warehouse-pilot-assessments/evaluate` endpoint remains evaluation-only. The new `POST /warehouse-pilot-assessments/evaluate-and-persist` endpoint invokes the existing `WarehousePilotService`, validates its result, snapshots the decision, and persists a new assessment.

The evaluator remains the only source of scoring and classification logic. This module does not duplicate or modify Module 3 scoring.

## Provenance and snapshots

Each assessment stores organization, Company, Warehouse, initiating User, evaluation version, final classification, and foreign keys to each contributing profile that exists at evaluation time: capability, company requirement, operational, commercial, and requirement assessment.

Because profiles are mutable, `result_snapshot` stores the complete evaluator response and `source_snapshot` stores the relevant Company, Warehouse, and profile column values at assessment time. JSON is used with PostgreSQL JSONB compatibility through the repository convention. This preserves explainability without changing source profiles.

## History and versioning

Assessments are append-only historical records. Company + Warehouse is intentionally not unique, so later reassessments create separate records. Version `v1` identifies the evaluator contract that produced the result.

## Tenant security

The endpoint derives organization ownership from persisted Company and Warehouse records. It requires organization write access for creation and organization access for retrieval. The request accepts only Company/Warehouse identifiers and cannot submit organization, scores, classifications, or actor attribution.

## Future boundary

The assessment is a future-safe source for Warehouse Pilot opportunity conversion. Pilot → Opportunity/Deal conversion is not implemented here. Capability Match conversion, outcome feedback, probability, forecasting, and autonomous execution are also outside this module.