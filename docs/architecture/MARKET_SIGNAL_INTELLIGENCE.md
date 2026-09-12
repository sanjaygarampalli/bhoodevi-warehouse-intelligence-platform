# Market Signal Intelligence Foundation

## 1. Business purpose

Market Signal Intelligence stores structured, traceable indications that a company
may develop warehouse or logistics demand. It is an upstream intelligence layer:

```text
Market Signal -> Evidence -> Demand Assessment -> Requirement Candidate
             -> Human Review -> Existing Requirement
```

A signal is not a confirmed requirement, and the module does not create leads,
requirements, companies, or warehouse matches automatically.

## 2. Architecture

The module contains three normalized domains:

- `MarketSignal`: organization-owned observation, optionally linked to an existing
  `Company`.
- `MarketSignalEvidence`: one or more concise source references supporting a signal.
- `RequirementCandidate`: a possible requirement inferred from a verified signal,
  requiring human review before conversion into the existing requirement workflow.

The service layer owns validation, deterministic assessment, candidate policy, and
deduplication. The API layer performs request validation and organization access
checks before delegating to the service.

## 3. Market Signal lifecycle

- `DETECTED`: newly recorded intelligence.
- `UNDER_REVIEW`: a researcher is evaluating the signal.
- `VERIFIED`: the organization accepts the signal/evidence as useful.
- `REJECTED`: the signal is incorrect or not useful; it cannot create a positive
  requirement candidate.
- `ARCHIVED`: historical/inactive intelligence.

## 4. Evidence model

A signal can have multiple evidence rows. Evidence stores source metadata, title,
short excerpt/summary, publication/recording dates, and an optional URL. Large
article bodies are intentionally not stored.

Evidence may be added before or after company linking. Evidence is scoped through
its parent signal, so cross-organization access is not possible through an evidence
identifier alone.

## 5. Evidence credibility

- `PRIMARY`: official company or government source.
- `HIGH`: trusted major news or verified industry source.
- `MEDIUM`: industry publication or secondary reporting.
- `LOW`: preliminary or unverified manual information.

Credibility is explanatory metadata. It does not independently prove warehouse
demand or automatically verify a signal.

## 6. Confidence meaning

Signal and candidate confidence is `LOW`, `MEDIUM`, or `HIGH`. It describes
confidence in the signal/evidence quality, not certainty that a company needs a
warehouse. A high-confidence signal remains a demand indication rather than a
confirmed commercial requirement.

## 7. Demand assessment logic

Assessment is deterministic and explainable; no LLM, external API, scraper, or
second lead-scoring engine is used.

- Strong: `NEW_WAREHOUSE`, `NEW_DISTRIBUTION_CENTER`, `LOGISTICS_EXPANSION`,
  `DISTRIBUTION_EXPANSION`.
- Moderate: `COMPANY_EXPANSION`, `ECOMMERCE_EXPANSION`, `MARKET_ENTRY`,
  `CAPACITY_EXPANSION`.
- Possible/context-dependent: `MANUFACTURING_EXPANSION`, `NEW_FACILITY`,
  `INDUSTRIAL_INVESTMENT`, `LAND_ACQUISITION`, `GOVERNMENT_TENDER`.
- Weak: `OTHER`.

Rejected signals return no positive demand indication. Archived signals do not
create new candidates. The response includes the signal type, status, evidence
count, demand strength, reasons, explanation, and recommended next step.

## 8. Why a signal is not automatically a requirement

Expansion, investment, land, or facility announcements can support many outcomes
that do not require leased warehouse space. The assessment therefore indicates
potential demand only. Candidate creation is restricted to verified, company-linked
signals with evidence or high signal confidence. Human review remains necessary.

## 9. Requirement Candidate lifecycle

- `CANDIDATE`: inferred possibility awaiting review.
- `UNDER_REVIEW`: actively evaluated by a user.
- `ACCEPTED`: human-approved candidate.
- `REJECTED`: human-rejected candidate.
- `CONVERTED`: reserved for a future explicit conversion workflow.

This module does not fabricate the fields required by the existing `Requirement`
model and does not implement automatic conversion.

## 10. Organization authorization

Every collection API requires an explicit `organization_id` and checks the existing
organization membership access utilities. Resource APIs load the resource first,
then authorize using its stored organization. Organization members can read;
`OWNER`, `ADMIN`, `MANAGER`, and `MEMBER` can write; viewers are read-only. Global
admins retain the existing system-wide bypass.

Company links are validated to belong to the same organization as the signal.

## 11. API endpoints

Market signals:

- `GET /market-signals`
- `POST /market-signals`
- `GET /market-signals/{signal_id}`
- `PATCH /market-signals/{signal_id}`

Evidence:

- `GET /market-signals/{signal_id}/evidence`
- `POST /market-signals/{signal_id}/evidence`
- `GET /market-signals/{signal_id}/evidence/{evidence_id}`
- `PATCH /market-signals/{signal_id}/evidence/{evidence_id}`

Intelligence and candidates:

- `GET /market-signals/{signal_id}/assessment`
- `POST /market-signals/{signal_id}/requirement-candidate`
- `GET /requirement-candidates`
- `GET /requirement-candidates/{candidate_id}`
- `PATCH /requirement-candidates/{candidate_id}`

Signal filters include organization, company, type, status, and confidence.
Candidate filters include organization, company, status, and demand strength.

## 12. Deduplication policy

The database enforces one `RequirementCandidate` per market signal. The service
also checks before insertion and returns a conflict for repeat creation. No fuzzy
company matching or inferred duplicate signal detection is attempted.

## 13. Future external ingestion architecture

Future ingestion adapters may normalize web research, news, company websites,
government announcements, tender portals, industry reports, or manual research into
the existing create-signal and add-evidence APIs. Adapters must preserve source
references and excerpts, avoid storing large scraped bodies, and never bypass
organization authorization or invent unsupported facts.

## 14. Explicit limitations

- No web scraping, browser automation, external APIs, or autonomous agents.
- No automatic company creation or entity resolution.
- No automatic existing-requirement, lead, deal, or warehouse-match creation.
- Existing lead, prospect-prioritization, action-intelligence, and warehouse-match
  scoring formulas are not modified.
- Candidate conversion is intentionally reserved for a future human-reviewed
  workflow that can supply the existing requirement fields safely.