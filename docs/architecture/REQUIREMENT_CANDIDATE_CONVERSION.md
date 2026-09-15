# Requirement Candidate → CRM Conversion

## Version 1 boundary

An `ACCEPTED` `RequirementCandidate` is explicitly converted through:

```text
RequirementCandidate → RequirementCandidateConversion → existing Company → Lead → Requirement
```

The candidate already has a required, organization-owned `company_id`, so Version 1 validates and reuses that Company. It does not create a duplicate Company or perform fuzzy matching. The source Market Signal and its evidence remain available through the candidate's existing `market_signal_id`.

## Explicit and auditable conversion

`POST /workflow/requirement-candidates/{candidate_id}/convert` requires an explicit lead number and permits only real optional CRM/requirement values. The service uses the existing Lead and Requirement services through transaction-aware methods, marks the candidate `CONVERTED` only after all records are ready, and stores the resulting Company, Lead, Requirement, organization, actor, and timestamps in `RequirementCandidateConversion`.

The conversion table has a unique candidate foreign key, so a successful retry returns the same records with `created: false`. Conversion is limited to `ACCEPTED` candidates; rejected, review, and unreviewed candidates cannot create CRM records.

## Tenant and transaction safety

The API requires organization write access derived from the candidate. The service independently validates candidate, Company, and Market Signal ownership. The conversion, Lead, Requirement, and candidate status update share one transaction; downstream failure rolls back all records and leaves the candidate unchanged.

The current Company schema has no organization/name uniqueness constraint. This workflow does not broaden duplicate matching beyond the candidate's authoritative Company relationship.

## Deliberate limitations

RequirementCandidate does not contain decision-maker, area, budget, warehouse type, or lease facts. Those values are not fabricated. They may be supplied explicitly in the conversion request. No new Requirement model, enrichment integration, outreach, forecasting, or Deal creation is included.