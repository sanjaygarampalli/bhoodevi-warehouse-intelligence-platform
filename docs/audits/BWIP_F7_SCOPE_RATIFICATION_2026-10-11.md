# BWIP F7 Decision-Maker Intelligence — Scope Ratification and Implementation Plan

**Date:** 2026-10-11 | **Repository:** E:\BHOODEVI-Warehouse-Intelligence-Platform | **Branch:** feature/company-module | **HEAD:** a32bf6b03a174c4a046df75538ddca8c75bbe5f0 | **Report:** docs/audits/BWIP_F7_SCOPE_RATIFICATION_2026-10-11.md
**Status:** PROPOSED — owner ratification required. No code, migration, or database change authorized by this plan.
**Source Proposal (preserved, not overwritten):** `docs/development/F7_SCOPE_PROPOSAL.md` (10,847 bytes, 2026-10-11)
**Prior closure (preserved):** `docs/audits/BWIP_F6_CLOSURE_2026-10-11_requirement-list-search-status.md` (F6 8/8 workflows PASS, disposable PG)
**Safety:** No `git reset/clean/commit/push`, no `bwip_db` writes, no app/frontend/migration/test edits in this task. Secrets redacted. Verified facts vs proposals vs open decisions are separated.

---

## 0. How to read this document

- **Verified fact:** observed in this checkout (HEAD a32bf6b, files, migrations, models, routes, frontend, browser evidence).
- **Proposed:** from `F7_SCOPE_PROPOSAL.md`; not yet ratified or implemented.
- **Open decision:** requires explicit owner choice before any implementation begins.

F6 was declared **CLOSED** after adding the single missing Requirement Intelligence list/search/status browser spec (`qa.e2e.ts` 8→9 specs, expected 12→13) and passing 4 disposable-PG rehearsals. That does **NOT** imply the overall browser suite is green — `company.e2e.ts` retains 5 known failures out-of-scope for F6. F7 must not hide or re-attribute those.

---

## 1. Repository baseline (verified)

**Git / migrations (verified):**

- HEAD `a32bf6b03a174c4a046df75538ddca8c75bbe5f0` on `feature/company-module` (from `git rev-parse` / `git branch --show-current`). `git status --short` shows ~32 M + ~27 ?? (all preserved; no reset/clean/commit/push performed in this task).
- Alembic chain head `x9c0d1e2f3a4` (`google_sign_in`: adds `users.google_subject` unique + `google_login_challenges`), predecessor `w8b9c0d1e2f3` (`session_revocation_rate_limits`: `users.token_version`, `rate_limit_buckets`). Prior F6 reports confirm 46 tables in `bwip_db` at `w8`, with `LIKE 'bwip_followup_%' = 0` after disposables dropped. New F6 migrations `t5` (requirement intelligence) through `x9` remain untracked but present.
- No F7 model, migration, endpoint, or UI has been implemented — confirmed by `app/models/__init__.py` (exports DecisionMaker, CompanyContact, ContactInvestigation, ResponseQualificationAssessment, RequirementIntelligenceEvidence, F5CompanyProfile, etc., but no TenantPerson/employment/role), `app/api/v1/routes.py` (no `/f7` router), and `frontend/src/App.tsx` / `Sidebar.tsx` (no `/people` or `/f7` routes).

**Auth / tenant isolation (verified):**

- `app/dependencies.py:get_current_user` decodes bearer token, checks `email`, `is_active`, and `payload.ver == user.token_version` (session revocation).
- `app/services/organization_access.py`: `require_organization_access` (ACTIVE membership or global admin role `admin`), `require_organization_write` (adds `WRITE_ROLES = OWNER/ADMIN/MANAGER/MEMBER`, denied for `VIEWER`), `organization_for_company(db, company_id)` resolves tenant via `Company.organization_id`. `is_global_admin` bypasses tenant for reads.
- `app/models/organization_membership.py`: `OrganizationMembership` unique `(user_id, organization_id)`, roles OWNER/ADMIN/MANAGER/MEMBER/VIEWER, status ACTIVE/INACTIVE. `app/models/user.py`: `token_version`, `google_subject` unique.

**Frontend / navigation (verified):**

- `frontend/src/routing/Router.tsx` + `App.tsx`: routes `/command-center`, `/companies`, `/companies/:id`, `/f5/companies`, `/f5/companies/:id`, `/requirement-intelligence`, `/requirement-intelligence/:id`, `/market-intelligence`, etc. Fallback renders placeholder title.
- `frontend/src/components/navigation/Sidebar.tsx` navGroups: Command Center, Market Intelligence, **Companies** (Companies, Company Intelligence `/f5/companies`, Contacts `/companies/contacts` placeholder, Decision Makers `/companies/decision-makers` placeholder), Warehouses, Opportunities (Requirement Intelligence `/requirement-intelligence`), Engagement, Intelligence. No F7 people/employment pages exist; Contacts/Decision Makers links are placeholders.
- `frontend/src/pages/RequirementIntelligencePage.tsx` pattern established for F6: 180ms debounce, `status IN ACTIVE/DRAFT/CLOSED`, `requestId` stale guard, `waitForListStable(300ms+Loading 0)` pattern reused for org switching. This pattern must be reused for F7 to avoid duplicating architecture.

**Deployment / safety (verified):**

- `docs/operations/DEPLOYMENT.md`: requires PostgreSQL, TLS reverse proxy, secret store for `DATABASE_URL`/`SECRET_KEY`, disposable-PG migration rehearsal before `alembic upgrade head`, no `alembic downgrade` as production rollback, previous image + verified backup restore preferred.
- `docs/architecture/F5_COMPATIBILITY_BOUNDARY.md` and `docs/architecture/DATABASE_DESIGN.md §4.4/§11.2` confirm F5 is additive under `/f5` and that the design envisaged `decision_makers` as the sole person record — but the repository actually contains normalized `CompanyContact`/`CompanyContactMethod` already. This is the central reconciliation point for F7.


## 1b. Existing capabilities to reuse (verified) and gaps

| System | Verified location | What to reuse | Gap F7 must fill |
|---|---|---|---|
| Company identity | `app/models/company.py` (`companies.organization_id`, index `ix_companies__organization_id`) + `organization_for_company()` | Tenant ownership for every person/company link; all F7 reads/writes resolve `Company.organization_id == organization_id` | None — mandatory re-check |
| Legacy DecisionMaker | `app/models/decision_maker.py` (flat `email/phone/linkedin_url`, `decision_level`, `decision_maker_status`) + `app/api/v1/endpoints/decision_maker.py` (requires org write) + `app/models/lead.py` (`primary_decision_maker_id FK`) + `lead_activity.decision_maker_id` | Keep IDs/FKs alive; treat as compatibility projection only | No provenance, no employment history, no verified authority |
| Normalized contacts | `app/models/company_intelligence.py: CompanyContact` (`organization_id`, `company_id`, `full_name`/`job_title`/`department`/`seniority`, `methods` relationship) + `CompanyContactMethod` (unique `(contact_id, method_type, normalized_value)`, partial unique `is_primary`, `verification_status` enum) + `app/services/company_intelligence.py` (validation, duplicate check via service, not DB cross-contact) + `app/api/v1/endpoints/company_intelligence.py` | Durable `(organization_id, company_id)` relationship entity; keep IDs so `contact_workflow` and `response_qualification` FKs stay intact | `person_id` not yet present; cross-contact duplicate check not concurrency-safe; no DB-level person/company uniqueness |
| Investigation / outreach | `app/models/contact_workflow.py: ContactInvestigation` (1 row/contact, booleans `designation_verified`, `email_verified`, etc.) + `ContactOutreachActivity` + `app/models/response_qualification.py: ResponseQualificationAssessment` (human_review_required, observed_facts, recommendation) | Reuse `contact_id` FK target; keep outreach history | Single mutable investigation row ≠ immutable field-level evidence history |
| Evidence provenance precedent | `app/models/f5_company_intelligence.py: F5EvidenceClaim` (claim/classification/source/published_at/observed_at/freshness) + `app/models/requirement_intelligence.py: RequirementIntelligenceEvidence` (source/source_url/observed_evidence/inference/classification/evidence_date/verification_status/verified_at/verified_by_user_id/confidence) + `app/services/f5_company_intelligence.py:freshness_for_dates()` (FRESH ≤90d, AGING 91-365d, STALE >365d) | Exact shape to copy for person/employment/role evidence; reuse freshness helper | No person-scoped evidence table yet |
| Tenant access | `app/services/organization_access.py` + `app/dependencies.py` + `app/models/organization_membership.py` | Every F7 endpoint uses `require_organization_access/write` with explicit `organization_id` query/body param | Must reject unscoped lists and cross-tenant joins |
| Frontend patterns | `RequirementIntelligencePage.tsx` (debounce 180ms, `requestId`/`active` guard, `waitForListStable`), `F5CompaniesPage.tsx` (server pagination, deterministic order), `useOrganizationWrite`, `organizationContext` | Reuse for F7 list/detail/search/status/freshness filters | No `/people` UI exists yet |
| Rate limiting / sessions | `app/models/rate_limit.py`, `app/core/rate_limit.py`, `DATABASE_DESIGN.md` quotas | Shared PG rate buckets reused for F7 expensive routes | No F7-specific quota needed initially |

**Migrations / architecture conventions:** `alembic/versions` naming `s4..x9`, `_enum_type`/`_json_type` helpers, `UniqueConstraint`/`Index` with `sqlite_where`/`postgresql_where`, composite FK pattern used by F5 (`(organization_id, company_id)`), and `docs/architecture/F5_COMPATIBILITY_BOUNDARY.md` additive-only boundary — all must be followed for F7.



## 1b. Existing capabilities to reuse (verified) and gaps

| System | Verified location | What to reuse | Gap F7 must fill |
|---|---|---|---|
| Company identity | `app/models/company.py` (`companies.organization_id`, index `ix_companies__organization_id`) + `organization_for_company()` | Tenant ownership for every person/company link; all F7 reads/writes resolve `Company.organization_id == organization_id` | None — mandatory re-check |
| Legacy DecisionMaker | `app/models/decision_maker.py` (flat `email/phone/linkedin_url`, `decision_level`, `decision_maker_status`) + `app/api/v1/endpoints/decision_maker.py` (requires org write) + `app/models/lead.py` (`primary_decision_maker_id FK`) + `lead_activity.decision_maker_id` | Keep IDs/FKs alive; treat as compatibility projection only | No provenance, no employment history, no verified authority |
| Normalized contacts | `app/models/company_intelligence.py: CompanyContact` (`organization_id`, `company_id`, `full_name`/`job_title`/`department`/`seniority`, `methods` relationship) + `CompanyContactMethod` (unique `(contact_id, method_type, normalized_value)`, partial unique `is_primary`, `verification_status` enum) + `app/services/company_intelligence.py` (validation, duplicate check via service, not DB cross-contact) + `app/api/v1/endpoints/company_intelligence.py` | Durable `(organization_id, company_id)` relationship entity; keep IDs so `contact_workflow` and `response_qualification` FKs stay intact | `person_id` not yet present; cross-contact duplicate check not concurrency-safe; no DB-level person/company uniqueness |
| Investigation / outreach | `app/models/contact_workflow.py: ContactInvestigation` (1 row/contact, booleans `designation_verified`, `email_verified`, etc.) + `ContactOutreachActivity` + `app/models/response_qualification.py: ResponseQualificationAssessment` (human_review_required, observed_facts, recommendation) | Reuse `contact_id` FK target; keep outreach history | Single mutable investigation row ≠ immutable field-level evidence history |
| Evidence provenance precedent | `app/models/f5_company_intelligence.py: F5EvidenceClaim` (claim/classification/source/published_at/observed_at/freshness) + `app/models/requirement_intelligence.py: RequirementIntelligenceEvidence` (source/source_url/observed_evidence/inference/classification/evidence_date/verification_status/verified_at/verified_by_user_id/confidence) + `app/services/f5_company_intelligence.py:freshness_for_dates()` (FRESH ≤90d, AGING 91-365d, STALE >365d) | Exact shape to copy for person/employment/role evidence; reuse freshness helper | No person-scoped evidence table yet |
| Tenant access | `app/services/organization_access.py` + `app/dependencies.py` + `app/models/organization_membership.py` | Every F7 endpoint uses `require_organization_access/write` with explicit `organization_id` query/body param | Must reject unscoped lists and cross-tenant joins |
| Frontend patterns | `RequirementIntelligencePage.tsx` (debounce 180ms, `requestId`/`active` guard, `waitForListStable`), `F5CompaniesPage.tsx` (server pagination, deterministic order), `useOrganizationWrite`, `organizationContext` | Reuse for F7 list/detail/search/status/freshness filters | No `/people` UI exists yet |
| Rate limiting / sessions | `app/models/rate_limit.py`, `app/core/rate_limit.py`, `DATABASE_DESIGN.md` quotas | Shared PG rate buckets reused for F7 expensive routes | No F7-specific quota needed initially |

**Migrations / architecture conventions:** `alembic/versions` naming `s4..x9`, `_enum_type`/`_json_type` helpers, `UniqueConstraint`/`Index` with `sqlite_where`/`postgresql_where`, composite FK pattern used by F5 (`(organization_id, company_id)`), and `docs/architecture/F5_COMPATIBILITY_BOUNDARY.md` additive-only boundary — all must be followed for F7.



## 2. Review of the F7 proposal — is a new person entity justified?

**Short answer: Yes, but only as a tenant-local identity with additive `CompanyContact.person_id`, not as a replacement or third contact store.**

Evidence:

- Draft `DATABASE_DESIGN.md` assumed `decision_makers` was the sole person record. The repository disproves that: `CompanyContact` is already the richer, normalized, relationship-scoped contact with methods, investigation, outreach, and qualification FKs. Creating another independent person store would duplicate `CompanyContact` for the third time.
- `CompanyContact` without a person cannot represent: (a) the same human working at two companies within one tenant, (b) a rehire, (c) a name correction that should propagate to both companies. `DecisionMaker` cannot either — flat, per-company, no provenance.
- The proposal's **TenantPerson + CompanyContact(person_id)** correctly makes `CompanyContact` the durable person/company relationship and `TenantPerson` the durable identity. Same known person at two companies = one `TenantPerson` + two `CompanyContact` rows. Different tenants never share a `TenantPerson`.

### 2.1 Per-proposed-change analysis (1 of 2)

| # | Proposal | Business need | Existing reusable | Why necessary | Tenant isolation | Duplicate / ambiguous | Evidence / provenance | Migration / back-compat | Test strategy | Alternatives |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **TenantPerson (new)** — `id, organization_id, display_name, lifecycle, created_by_user_id, created_at` + optional `tenant_person_source_keys(org, namespace, external_id)` unique | Distinguish same human across companies vs colliding names | Nothing equivalent; `CompanyContact` is per-company | Without it, rehire/multi-company person duplicates; corrections diverge | Must be strictly tenant-local; composite unique `(org, id)` so children FK `(org, person_id)`; no global directory | Names NOT unique; same-name/email-similarity/shared mailbox never auto-merge | Per-field evidence with `source/source_url/observed_at/evidence_date/classification/review_status/recorder/verifier` ; `UNKNOWN` when dates absent | Additive, nullable migration, synthetic fixtures only; production backfill after dry-run + rehearsal | Concurrent same source key -> one 201 one 409 via DB unique | Alt: keep per-company only -> rejected. Alt: global person -> rejected |
| 2 | **CompanyContact.person_id (additive)** — nullable FK to `TenantPerson`, partial unique `(org, company, person) WHERE person_id NOT NULL`, FK `(org, person) -> (org, id)` | Durable person/company relationship preserving IDs | `CompanyContact.id` already targeted by method/investigation/outreach/qualification | Identity must not churn contact IDs or outreach history breaks | Composite FK guarantees same tenant; tenant reassignment forbidden | Duplicate `(org, company, person)` via DB unique; cross-tenant person_id -> 403 | Existing `first_name/last_name/full_name/job_title` become compatibility projections; not separately writable after mapping | Add column nullable; old rows NULL = unmapped; mapped only after review | Existence+unique violation; NULL rows render unmapped | Alt: new join table -> rejected (churn) |
| 3 | **ContactEmployment (new)** — `id, org, company, contact, start_date, end_date, status CURRENT/FORMER/UNKNOWN`, partial unique `CURRENT` per contact | Model current/former, rehire, UNKNOWN dates | No employment history; current row implicit | Need episodes for authority timing and rehires | FK `(org, company, contact)` validated | Only one `CURRENT` per contact; competing CURRENT -> review queue | Per-employment evidence; future observed date -> 422 | Additive; legacy row preserved as episode only if dates known else UNKNOWN | UNKNOWN, ordering, CURRENT uniqueness, rehire tests | Alt: infer from updated_at -> rejected |
| 4 | **ContactProfessionalRole (new)** — `id, employment_id, org, company, title/dept/seniority/geography/authority DECISION_MAKER/INFLUENCER/UNKNOWN`, concurrent roles allowed | Distinguish title from buying authority | `ContactSeniority` + `DecisionLevel` enums flat | Title alone must not prove authority | Linked to `ContactEmployment`, same tenant/company | Multiple roles per employment allowed; authority per role | Per-role evidence; authority requires source | Additive; legacy DecisionMaker maps after review only | Multi-role overlap, UNKNOWN without evidence | Alt: single role column -> insufficient |


### 2.1 Per-proposed-change analysis (2 of 2)

| # | Proposal | Business need | Existing reusable | Why necessary | Tenant isolation | Duplicate / ambiguous | Evidence / provenance | Migration / back-compat | Test strategy | Alternatives |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | **Person/Employment/Role evidence (new)** — typed `target_id` FK to specific parent | Immutable provenance, correction by superseding | No immutable field-level history; `ContactInvestigation` single mutable row | Verified claims must be append-only | Must carry `org`, direct FK to correct parent (no generic polymorphic key) | Generic polymorphic key would let row point to any tenant's record | FACT/INFERENCE/UNKNOWN, review status, actor/time immutable after VERIFIED; `confidence` NULL without ratified formula | Seed legacy as UNVERIFIED/UNKNOWN only; verified after human review | Immutability (verified -> 409), freshness per assertion | Alt: reuse f5_evidence_claims -> rejected |
| 6 | **CompanyContactMethod reuse** — no duplication | Display verified methods read-only | Methods scoped to `contact_id` with uniqueness | F7 must not re-verify or re-acquire details | Methods relationship-scoped; address never propagates | Repeated value for same canonical contact reuses one method; uncertain shared address -> review | F8 owns acquisition/normalization/freshness | No method schema change; F8 extends same IDs | Duplicate across persons same tenant/company -> 409 or REVIEW | Alt: new person-level methods -> rejected |
| 7 | **Legacy DecisionMaker adapter** — `legacy_decision_maker_mapping(legacy_id UNIQUE, contact_id, employment_id)` | Preserve commercial Lead/Activity links | `DecisionMaker.id` referenced by Lead/Activity | Cannot drop; pipeline loses FK | Mapping same-tenant/company only | Many legacy IDs -> one contact after resolution; both histories retained | Legacy fields projected; edits go through canonical service same tx | No cascade delete; rollback retains history | Adapter projection + rollback fixture | Alt: migrate FKs directly -> destructive |

### 2.2 Cross-cutting proposal risks confirmed

- **Verification-role dilution:** Proposal says “verification uses explicitly authorized human write roles initially.” Verified — currently `require_organization_write` allows MEMBER. Owner must decide whether verification should require MANAGER+ or OWNER/ADMIN only (separation-of-duties).
- **Confidence numeric:** Proposal correctly keeps `confidence` NULL unless ratified. Do NOT invent a score.
- **Cross-tenant leakage:** No global directory, no global email uniqueness, no cross-tenant duplicate hints, no automatic evidence propagation — as proposed and required.
- **Freshness thresholds:** `FRESH <=90, AGING 91-365, STALE >365, UNKNOWN` are **proposed for employment/role**, not ratified business truth. Implement as explicit function (`freshness_for_dates`) and label thresholds configurable.
- **Compatibility writes:** “Retain old response shapes and IDs, update projections in same transaction. No dual writes” — ratify; dual writes diverge under concurrency.



## 1b. Existing capabilities to reuse (verified) and gaps

| System | Verified location | What to reuse | Gap F7 must fill |
|---|---|---|---|
| Company identity | `app/models/company.py` (`companies.organization_id`, index `ix_companies__organization_id`) + `organization_for_company()` | Tenant ownership for every person/company link; all F7 reads/writes resolve `Company.organization_id == organization_id` | None — mandatory re-check |
| Legacy DecisionMaker | `app/models/decision_maker.py` (flat `email/phone/linkedin_url`, `decision_level`, `decision_maker_status`) + `app/api/v1/endpoints/decision_maker.py` (requires org write) + `app/models/lead.py` (`primary_decision_maker_id FK`) + `lead_activity.decision_maker_id` | Keep IDs/FKs alive; treat as compatibility projection only | No provenance, no employment history, no verified authority |
| Normalized contacts | `app/models/company_intelligence.py: CompanyContact` (`organization_id`, `company_id`, `full_name`/`job_title`/`department`/`seniority`, `methods` relationship) + `CompanyContactMethod` (unique `(contact_id, method_type, normalized_value)`, partial unique `is_primary`, `verification_status` enum) + `app/services/company_intelligence.py` (validation, duplicate check via service, not DB cross-contact) + `app/api/v1/endpoints/company_intelligence.py` | Durable `(organization_id, company_id)` relationship entity; keep IDs so `contact_workflow` and `response_qualification` FKs stay intact | `person_id` not yet present; cross-contact duplicate check not concurrency-safe; no DB-level person/company uniqueness |
| Investigation / outreach | `app/models/contact_workflow.py: ContactInvestigation` (1 row/contact, booleans `designation_verified`, `email_verified`, etc.) + `ContactOutreachActivity` + `app/models/response_qualification.py: ResponseQualificationAssessment` (human_review_required, observed_facts, recommendation) | Reuse `contact_id` FK target; keep outreach history | Single mutable investigation row ≠ immutable field-level evidence history |
| Evidence provenance precedent | `app/models/f5_company_intelligence.py: F5EvidenceClaim` (claim/classification/source/published_at/observed_at/freshness) + `app/models/requirement_intelligence.py: RequirementIntelligenceEvidence` (source/source_url/observed_evidence/inference/classification/evidence_date/verification_status/verified_at/verified_by_user_id/confidence) + `app/services/f5_company_intelligence.py:freshness_for_dates()` (FRESH ≤90d, AGING 91-365d, STALE >365d) | Exact shape to copy for person/employment/role evidence; reuse freshness helper | No person-scoped evidence table yet |
| Tenant access | `app/services/organization_access.py` + `app/dependencies.py` + `app/models/organization_membership.py` | Every F7 endpoint uses `require_organization_access/write` with explicit `organization_id` query/body param | Must reject unscoped lists and cross-tenant joins |
| Frontend patterns | `RequirementIntelligencePage.tsx` (debounce 180ms, `requestId`/`active` guard, `waitForListStable`), `F5CompaniesPage.tsx` (server pagination, deterministic order), `useOrganizationWrite`, `organizationContext` | Reuse for F7 list/detail/search/status/freshness filters | No `/people` UI exists yet |
| Rate limiting / sessions | `app/models/rate_limit.py`, `app/core/rate_limit.py`, `DATABASE_DESIGN.md` quotas | Shared PG rate buckets reused for F7 expensive routes | No F7-specific quota needed initially |

**Migrations / architecture conventions:** `alembic/versions` naming `s4..x9`, `_enum_type`/`_json_type` helpers, `UniqueConstraint`/`Index` with `sqlite_where`/`postgresql_where`, composite FK pattern used by F5 (`(organization_id, company_id)`), and `docs/architecture/F5_COMPATIBILITY_BOUNDARY.md` additive-only boundary — all must be followed for F7.



## 2. Review of the F7 proposal — is a new person entity justified?

**Short answer: Yes, but only as a tenant-local identity with additive `CompanyContact.person_id`, not as a replacement or third contact store.**

Evidence:

- Draft `DATABASE_DESIGN.md` assumed `decision_makers` was the sole person record. The repository disproves that: `CompanyContact` is already the richer, normalized, relationship-scoped contact with methods, investigation, outreach, and qualification FKs. Creating another independent person store would duplicate `CompanyContact` for the third time.
- `CompanyContact` without a person cannot represent: (a) the same human working at two companies within one tenant, (b) a rehire, (c) a name correction that should propagate to both companies. `DecisionMaker` cannot either — flat, per-company, no provenance.
- The proposal's **TenantPerson + CompanyContact(person_id)** correctly makes `CompanyContact` the durable person/company relationship and `TenantPerson` the durable identity. Same known person at two companies = one `TenantPerson` + two `CompanyContact` rows. Different tenants never share a `TenantPerson`.

### 2.1 Per-proposed-change analysis (1 of 2)

| # | Proposal | Business need | Existing reusable | Why necessary | Tenant isolation | Duplicate / ambiguous | Evidence / provenance | Migration / back-compat | Test strategy | Alternatives |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **TenantPerson (new)** — `id, organization_id, display_name, lifecycle, created_by_user_id, created_at` + optional `tenant_person_source_keys(org, namespace, external_id)` unique | Distinguish same human across companies vs colliding names | Nothing equivalent; `CompanyContact` is per-company | Without it, rehire/multi-company person duplicates; corrections diverge | Must be strictly tenant-local; composite unique `(org, id)` so children FK `(org, person_id)`; no global directory | Names NOT unique; same-name/email-similarity/shared mailbox never auto-merge | Per-field evidence with `source/source_url/observed_at/evidence_date/classification/review_status/recorder/verifier` ; `UNKNOWN` when dates absent | Additive, nullable migration, synthetic fixtures only; production backfill after dry-run + rehearsal | Concurrent same source key -> one 201 one 409 via DB unique | Alt: keep per-company only -> rejected. Alt: global person -> rejected |
| 2 | **CompanyContact.person_id (additive)** — nullable FK to `TenantPerson`, partial unique `(org, company, person) WHERE person_id NOT NULL`, FK `(org, person) -> (org, id)` | Durable person/company relationship preserving IDs | `CompanyContact.id` already targeted by method/investigation/outreach/qualification | Identity must not churn contact IDs or outreach history breaks | Composite FK guarantees same tenant; tenant reassignment forbidden | Duplicate `(org, company, person)` via DB unique; cross-tenant person_id -> 403 | Existing `first_name/last_name/full_name/job_title` become compatibility projections; not separately writable after mapping | Add column nullable; old rows NULL = unmapped; mapped only after review | Existence+unique violation; NULL rows render unmapped | Alt: new join table -> rejected (churn) |
| 3 | **ContactEmployment (new)** — `id, org, company, contact, start_date, end_date, status CURRENT/FORMER/UNKNOWN`, partial unique `CURRENT` per contact | Model current/former, rehire, UNKNOWN dates | No employment history; current row implicit | Need episodes for authority timing and rehires | FK `(org, company, contact)` validated | Only one `CURRENT` per contact; competing CURRENT -> review queue | Per-employment evidence; future observed date -> 422 | Additive; legacy row preserved as episode only if dates known else UNKNOWN | UNKNOWN, ordering, CURRENT uniqueness, rehire tests | Alt: infer from updated_at -> rejected |
| 4 | **ContactProfessionalRole (new)** — `id, employment_id, org, company, title/dept/seniority/geography/authority DECISION_MAKER/INFLUENCER/UNKNOWN`, concurrent roles allowed | Distinguish title from buying authority | `ContactSeniority` + `DecisionLevel` enums flat | Title alone must not prove authority | Linked to `ContactEmployment`, same tenant/company | Multiple roles per employment allowed; authority per role | Per-role evidence; authority requires source | Additive; legacy DecisionMaker maps after review only | Multi-role overlap, UNKNOWN without evidence | Alt: single role column -> insufficient |


### 2.1 Per-proposed-change analysis (2 of 2)

| # | Proposal | Business need | Existing reusable | Why necessary | Tenant isolation | Duplicate / ambiguous | Evidence / provenance | Migration / back-compat | Test strategy | Alternatives |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | **Person/Employment/Role evidence (new)** — typed `target_id` FK to specific parent | Immutable provenance, correction by superseding | No immutable field-level history; `ContactInvestigation` single mutable row | Verified claims must be append-only | Must carry `org`, direct FK to correct parent (no generic polymorphic key) | Generic polymorphic key would let row point to any tenant's record | FACT/INFERENCE/UNKNOWN, review status, actor/time immutable after VERIFIED; `confidence` NULL without ratified formula | Seed legacy as UNVERIFIED/UNKNOWN only; verified after human review | Immutability (verified -> 409), freshness per assertion | Alt: reuse f5_evidence_claims -> rejected |
| 6 | **CompanyContactMethod reuse** — no duplication | Display verified methods read-only | Methods scoped to `contact_id` with uniqueness | F7 must not re-verify or re-acquire details | Methods relationship-scoped; address never propagates | Repeated value for same canonical contact reuses one method; uncertain shared address -> review | F8 owns acquisition/normalization/freshness | No method schema change; F8 extends same IDs | Duplicate across persons same tenant/company -> 409 or REVIEW | Alt: new person-level methods -> rejected |
| 7 | **Legacy DecisionMaker adapter** — `legacy_decision_maker_mapping(legacy_id UNIQUE, contact_id, employment_id)` | Preserve commercial Lead/Activity links | `DecisionMaker.id` referenced by Lead/Activity | Cannot drop; pipeline loses FK | Mapping same-tenant/company only | Many legacy IDs -> one contact after resolution; both histories retained | Legacy fields projected; edits go through canonical service same tx | No cascade delete; rollback retains history | Adapter projection + rollback fixture | Alt: migrate FKs directly -> destructive |

### 2.2 Cross-cutting proposal risks confirmed

- **Verification-role dilution:** Proposal says “verification uses explicitly authorized human write roles initially.” Verified — currently `require_organization_write` allows MEMBER. Owner must decide whether verification should require MANAGER+ or OWNER/ADMIN only (separation-of-duties).
- **Confidence numeric:** Proposal correctly keeps `confidence` NULL unless ratified. Do NOT invent a score.
- **Cross-tenant leakage:** No global directory, no global email uniqueness, no cross-tenant duplicate hints, no automatic evidence propagation — as proposed and required.
- **Freshness thresholds:** `FRESH <=90, AGING 91-365, STALE >365, UNKNOWN` are **proposed for employment/role**, not ratified business truth. Implement as explicit function (`freshness_for_dates`) and label thresholds configurable.
- **Compatibility writes:** “Retain old response shapes and IDs, update projections in same transaction. No dual writes” — ratify; dual writes diverge under concurrency.



## 3. Business workflow — identity ambiguity stays visible

```
Company (tenant-owned, organization_id)
  └─ CompanyContact (organization_id, company_id) — durable relationship, keeps its id
       ├─ person_id → TenantPerson (organization_id, id) — ONE human per tenant
       │    └─ evidence: name/lifecycle assertions (source, observed_at, evidence_date, FACT/INFERENCE/UNKNOWN, review_status, verifier/time, superseded_by)
       ├─ CompanyContactMethod (per relationship, verification_status) — F8-owned, F7 read-only
       ├─ ContactEmployment (per relationship, CURRENT/FORMER/UNKNOWN + dates) — one CURRENT per contact max
       │    ├─ employment evidence (same shape)
       │    └─ ContactProfessionalRole (title/department/seniority/geography/authority DECISION_MAKER/INFLUENCER/UNKNOWN)
       │         └─ role/authority evidence (separate source needed; title ≠ authority)
       ├─ ContactInvestigation (legacy, 1 row/contact, booleans) — preserved as legacy fact
       ├─ ContactOutreachActivity / ResponseQualificationAssessment — preserved
       └─ LegacyDecisionMakerMapping — keeps Lead/Activity FK history
```

**Workflow (human-controlled, no automatic side effects):**

1. **Company** exists. Cannot attach person without validated `Company.organization_id`.
2. **Possible person** created with `display_name` only; optional `source_namespace/external_id` attached *only after* review (unique `(org, namespace, external_id)`).
3. **Verified identity** after reviewer verifies evidence (`source/source_url/observed_at/evidence_date/classification/verifier/verified_at`). Verified row immutable; correction = new superseding row.
4. **Employment episode** links person↔company with `start_date/end_date/status`; only one `CURRENT` per contact; competing `CURRENT` quarantined.
5. **Decision-maker role** within employment with title/department/seniority/geography and authority; multiple concurrent roles allowed; authority per role needs own evidence.
6. **Contact methods** remain on `CompanyContact`; F7 displays read-only; F8 owns verification/provenance; method duplication across persons in same `(org, company)` conflicts.
7. Identity ambiguity (similar names, shared mailbox) stays visible as `POSSIBLE_DUPLICATE / REVIEW_REQUIRED`; demand side never treated as bulk resolved. **No auto lead/requirement/opportunity/deal/outreach** as side effect of discovery.

Any “verified contact” optimism is out-of-scope until F8. F7 never infers employment from a phone/email value.



## 4. Security and data-integrity acceptance (all must be demonstrable before DONE)

| # | Requirement | Acceptance criterion (objective) | How it will be proved |
|---|---|---|---|
| S1 | Org-scoped reads/writes | Every F7 list/detail/mutation requires explicit `organization_id` (query/body) with ACTIVE membership (or explicit org context for global admin). Unscoped list → 400/422, no silent enumeration. | API tests with missing org → 422; correct org → 200. Follows F5 precedent rejecting global admin without `organization_id`. |
| S2 | Company ownership check | `Company.organization_id == organization_id` verified for every person/company/employment/role create; mismatch → 403 with tenant-safe message. | Cross-company fixture: create person in Org A, attempt link to Org B company → 403, no existence oracle. |
| S3 | Identity uniqueness + concurrency | `tenant_person_source_keys` unique `(org, namespace, external_id)` WHERE not null; `company_contacts` partial unique `(org, company, person)` WHERE `person_id` not null; `contact_employment` partial unique `CURRENT` per `contact_id`. Concurrent duplicate creates via 2 PG transactions → one 201, one 409 (`IntegrityError` handled). | PG concurrency harness (row-lock/idempotent/unique) mirroring `postgres-concurrency.json` pattern from F6. Service-level duplicate scan alone is insufficient. |
| S4 | Ambiguous matches | Similar names (e.g., `Pvt Ltd` normalized vs `Private Limited` — `normalize_company_name` precedent), email similarity, shared mailbox **never** auto-merge. Flagged `POSSIBLE_DUPLICATE`/`REVIEW_REQUIRED`; canonical promotion requires explicit `resolve` with evidence. | Tests: same normalized name → still separate until `resolve`; shared method value across two persons same `(org, company)` → 409 or queued review, not propagated identity. |
| S5 | Evidence provenance | Every assertion stores `source/source_url/observed_at/evidence_date/classification/review_status/recorder/reviewer/verifier/verified_at/superseded_by_id`. `VERIFIED` rows immutable (409 on direct edit); correction via new superseding row retaining original. `confidence` NULL unless ratified. | Evidence integrity suite: verify transition `UNVERIFIED→VERIFIED` records actor/time; attempt edit verified → 409; `superseded_by` chain preserved. |
| S6 | Freshness (proposed thresholds) | Per-assertion `freshness_for_dates(observed_at, evidence_date)` → FRESH ≤90d / AGING 91-365d / STALE >365d / UNKNOWN (no date), using newest date. Viewing/editing profile never refreshes dates; `last_verified_at` is separate from `evidence_date`. | Boundary tests at 90d/91d/365d/366d + UNKNOWN null case; prove no side-effect on profile read. Thresholds labeled configurable, not approved business truth. |
| S7 | Contact-method verification | F7 is read-only for methods (reuse `CompanyContactMethod.verification_status`); F8 owns acquisition/normalization/provenance/freshness/primary selection. Method address verification never propagates to another employment/company. | F7 tests show method read via `CompanyContact` but no F7 write; F8 reuse check: same canonical method reused for same person, not duplicated. |
| S8 | Account / membership boundaries | VIEWER denied on every mutation (POST/PATCH/verify/resolve) → 403. Revoked membership/token_version increment effective immediately on next request (no restart needed). | Tests: VIEWER fixtures for each mutation; deactivate membership mid-session → next F7 request 403 (uses `get_active_membership` + `token_version`). |
| S9 | Migration & rollback safety | Additive tables + nullable FK only; dry-run inventory first; no customer backfill without authorized rehearsal; rollback disables routes/UI, retains tables/history/mapping snapshot, forward corrective migration preferred over downgrade in production. | Disposable PG rehearsals: upgrade→downgrade→re-upgrade with row counts + unicode alias preservation (as F6 `verify_f6_migrations` pattern); rollback fixture: `Lead/Activity` FKs intact after disabling F7 routes. |
| S10 | API error contracts | Consistent JSON `{"detail": string, "code": string}` (code: `forbidden/access_denied`, `not_found`, `conflict/duplicate`, `validation_error`, `verification_forbidden`); correct HTTP 401/403/404/409/422; no token/secret leakage. | Contract tests for each code; redaction audit (no `SECRET_KEY` samples in logs). |
| S11 | Human-controlled resolution | No silent merges; ambiguous rows stay `REVIEW_REQUIRED` until `POST /resolve` with evidence and verifier; promotion idempotent; `hr_history` preserved. | Browser + API: unresolved row visible as conflict chip, resolve requires evidence payload; competing `CURRENT` stays quarantined. |
| S12 | Frontend states | Loading, empty, conflict/review, 401/403/404/network distinctive; stale-response discard via `requestId` guard (route delay 600ms) as in `RequirementIntelligencePage`. | Browser stale test: `page.route` delay 600ms on Org A, switch A→B → B wins after 800ms (reuse F6 `requirement-organization-b-no-stale-a` pattern). |



## 7. Verification plan (no implementation in this task — how F7 will be proved)

- **Pre-flight:** `git rev-parse HEAD` / `git branch --show-current` / `git status --short` preservation; `npm run typecheck && npm run build` must pass before any migration work (as F6 closure did, 3 builds).
- **Isolation:** Every DB touch uses `qa_environment.disposable_database(bwip_followup_+12hex)` / `make_url().set(database='postgres')` / `AUTOCOMMIT` / `WITH (FORCE)` / `count==0` — never `bwip_db` (expected `w8b9c0d1e2f3` lag, 46 tables, zero disposables).
- **Migration rehearsal:** Disposable upgrade→downgrade→re-upgrade + `SELECT LIKE 'bwip_followup_%'=0` (as `scripts/verify_f6_migrations.py` + `verify_followup_runtime.py`).
- **Suites:** API (CRUD/history), security (tenant/VIEWER/revocation), concurrency (DB uniques), evidence integrity (immutability/freshness), browser (list/detail/stale/read-only/conflict), backup/restore + postgres-concurrency harnesses — each with evidence JSON under `docs/development/evidence/` and redacted `SECRET_KEY`.

## 8. Deliverables of this plan

- This file `docs/audits/BWIP_F7_SCOPE_RATIFICATION_2026-10-11.md` (new, uniquely named; original proposal and prior audits `BWIP_F6_ISOLATED_REHEARSAL`, `BWIP_F6_RELEASE_GATE`, `BWIP_F6_CLOSURE`, `BWIP_MASTER_AUDIT` preserved).
- No report overwritten, no code/DB/migration/OAuth/F8 mutated, no destructive operation run.

---

## 9. Return summary (as requested)

- **Current repository baseline:** `feature/company-module @ a32bf6b`, head `x9c0d1e2f3a4`, ~32 M + ~27 ?? preserved, no F7 entity/route/UI yet, auth via `token_version`, tenant isolation via `require_organization_access/write`, two prior person-adjacent systems (`DecisionMaker` flat + `CompanyContact` normalized).
- **Existing F7-related capabilities:** Company ownership, normalized contacts/methods, investigation/outreach/qualification FKs, F5/Requirement evidence provenance + `freshness_for_dates`, tenant helpers, frontend debounce/stale-guard/pagination precedents — all reusable; gaps are TenantPerson/employment/role/typed evidence + duplicate review.
- **Review of proposed identity model:** Justified only as tenant-local `TenantPerson` + additive `CompanyContact.person_id` durable relationship; per-change table above with tenant, duplicate, evidence, migration, alternative analysis. Proposal's freshness thresholds, verification-role wording, and compatibility-write line need explicit owner decision before code.
- **Recommended F7 scope:** §5.1–5.13 with additive model, compatibility adapter, security S1–S12, acceptance matrix F7.1–F7.6, browser QA mirroring F6, and explicit non-goals (no scraping, no auto-creation, no cross-tenant hints).
- **Acceptance-criteria matrix:** S1–S12 (security/data-integrity, §4) and F7.1–F7.6 (§5.11) — all PROPOSED, not yet PASS, each with objective signal.
- **Decisions requiring approval:** D1–D10 above — owner must ratify scale, freshness thresholds, verification roles, legacy fate, method boundary, source-key gating, duplicate UX, projection semantics, backfill authorization, and evidence shape.
- **Exact next implementation prompt (use only after owner approval):**

```text
F7 Phase B — data layer only (no UI/routes). In a disposable PostgreSQL isolation (bwip_followup_+12hex, never bwip_db):
1. Run the read-only inventory script and attach the dry-run conflict list.
2. Create additive migration y1 (TenantPerson + TenantPersonSourceKey + ContactEmployment + ContactProfessionalRole + typed evidence + LegacyDecisionMakerMapping, plus CompanyContact.person_id nullable with composite FK (organization_id, person_id) and partial unique (org, company, person) WHERE not null).
3. Prove upgrade/downgrade/re-upgrade on disposable PG with schema/row-count/unicode preservation and single-head assertion; assert LIKE 'bwip_followup_%'=0 after drops.
4. Prove PG concurrent duplicate creation yields one canonical + 409 via DB uniques, and evidence immutability + freshness boundary tests (90/91/365/366/UNKNOWN).
Do not touch F7 routes/UI, do not backfill customer tenants, do not implement F8, and do not mutate bwip_db.
```

---

*Generated: 2026-10-11 | Branch feature/company-module @ a32bf6b | Source proposal docs/development/F7_SCOPE_PROPOSAL.md (10,847 bytes) preserved | Evidence: docs/audits/BWIP_F6_CLOSURE_2026-10-11_requirement-list-search-status.md + docs/audits/BWIP_F6_ISOLATED_REHEARSAL_2026-10-11.md + docs/development/evidence/2026-10-10/browser-results.json (expected 13, see F6 closure) — no new F7 implementation in this task.*



## 1b. Existing capabilities to reuse (verified) and gaps

| System | Verified location | What to reuse | Gap F7 must fill |
|---|---|---|---|
| Company identity | `app/models/company.py` (`companies.organization_id`, index `ix_companies__organization_id`) + `organization_for_company()` | Tenant ownership for every person/company link; all F7 reads/writes resolve `Company.organization_id == organization_id` | None — mandatory re-check |
| Legacy DecisionMaker | `app/models/decision_maker.py` (flat `email/phone/linkedin_url`, `decision_level`, `decision_maker_status`) + `app/api/v1/endpoints/decision_maker.py` (requires org write) + `app/models/lead.py` (`primary_decision_maker_id FK`) + `lead_activity.decision_maker_id` | Keep IDs/FKs alive; treat as compatibility projection only | No provenance, no employment history, no verified authority |
| Normalized contacts | `app/models/company_intelligence.py: CompanyContact` (`organization_id`, `company_id`, `full_name`/`job_title`/`department`/`seniority`, `methods` relationship) + `CompanyContactMethod` (unique `(contact_id, method_type, normalized_value)`, partial unique `is_primary`, `verification_status` enum) + `app/services/company_intelligence.py` (validation, duplicate check via service, not DB cross-contact) + `app/api/v1/endpoints/company_intelligence.py` | Durable `(organization_id, company_id)` relationship entity; keep IDs so `contact_workflow` and `response_qualification` FKs stay intact | `person_id` not yet present; cross-contact duplicate check not concurrency-safe; no DB-level person/company uniqueness |
| Investigation / outreach | `app/models/contact_workflow.py: ContactInvestigation` (1 row/contact, booleans `designation_verified`, `email_verified`, etc.) + `ContactOutreachActivity` + `app/models/response_qualification.py: ResponseQualificationAssessment` (human_review_required, observed_facts, recommendation) | Reuse `contact_id` FK target; keep outreach history | Single mutable investigation row ≠ immutable field-level evidence history |
| Evidence provenance precedent | `app/models/f5_company_intelligence.py: F5EvidenceClaim` (claim/classification/source/published_at/observed_at/freshness) + `app/models/requirement_intelligence.py: RequirementIntelligenceEvidence` (source/source_url/observed_evidence/inference/classification/evidence_date/verification_status/verified_at/verified_by_user_id/confidence) + `app/services/f5_company_intelligence.py:freshness_for_dates()` (FRESH ≤90d, AGING 91-365d, STALE >365d) | Exact shape to copy for person/employment/role evidence; reuse freshness helper | No person-scoped evidence table yet |
| Tenant access | `app/services/organization_access.py` + `app/dependencies.py` + `app/models/organization_membership.py` | Every F7 endpoint uses `require_organization_access/write` with explicit `organization_id` query/body param | Must reject unscoped lists and cross-tenant joins |
| Frontend patterns | `RequirementIntelligencePage.tsx` (debounce 180ms, `requestId`/`active` guard, `waitForListStable`), `F5CompaniesPage.tsx` (server pagination, deterministic order), `useOrganizationWrite`, `organizationContext` | Reuse for F7 list/detail/search/status/freshness filters | No `/people` UI exists yet |
| Rate limiting / sessions | `app/models/rate_limit.py`, `app/core/rate_limit.py`, `DATABASE_DESIGN.md` quotas | Shared PG rate buckets reused for F7 expensive routes | No F7-specific quota needed initially |

**Migrations / architecture conventions:** `alembic/versions` naming `s4..x9`, `_enum_type`/`_json_type` helpers, `UniqueConstraint`/`Index` with `sqlite_where`/`postgresql_where`, composite FK pattern used by F5 (`(organization_id, company_id)`), and `docs/architecture/F5_COMPATIBILITY_BOUNDARY.md` additive-only boundary — all must be followed for F7.



## 2. Review of the F7 proposal — is a new person entity justified?

**Short answer: Yes, but only as a tenant-local identity with additive `CompanyContact.person_id`, not as a replacement or third contact store.**

Evidence:

- Draft `DATABASE_DESIGN.md` assumed `decision_makers` was the sole person record. The repository disproves that: `CompanyContact` is already the richer, normalized, relationship-scoped contact with methods, investigation, outreach, and qualification FKs. Creating another independent person store would duplicate `CompanyContact` for the third time.
- `CompanyContact` without a person cannot represent: (a) the same human working at two companies within one tenant, (b) a rehire, (c) a name correction that should propagate to both companies. `DecisionMaker` cannot either — flat, per-company, no provenance.
- The proposal's **TenantPerson + CompanyContact(person_id)** correctly makes `CompanyContact` the durable person/company relationship and `TenantPerson` the durable identity. Same known person at two companies = one `TenantPerson` + two `CompanyContact` rows. Different tenants never share a `TenantPerson`.

### 2.1 Per-proposed-change analysis (1 of 2)

| # | Proposal | Business need | Existing reusable | Why necessary | Tenant isolation | Duplicate / ambiguous | Evidence / provenance | Migration / back-compat | Test strategy | Alternatives |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **TenantPerson (new)** — `id, organization_id, display_name, lifecycle, created_by_user_id, created_at` + optional `tenant_person_source_keys(org, namespace, external_id)` unique | Distinguish same human across companies vs colliding names | Nothing equivalent; `CompanyContact` is per-company | Without it, rehire/multi-company person duplicates; corrections diverge | Must be strictly tenant-local; composite unique `(org, id)` so children FK `(org, person_id)`; no global directory | Names NOT unique; same-name/email-similarity/shared mailbox never auto-merge | Per-field evidence with `source/source_url/observed_at/evidence_date/classification/review_status/recorder/verifier` ; `UNKNOWN` when dates absent | Additive, nullable migration, synthetic fixtures only; production backfill after dry-run + rehearsal | Concurrent same source key -> one 201 one 409 via DB unique | Alt: keep per-company only -> rejected. Alt: global person -> rejected |
| 2 | **CompanyContact.person_id (additive)** — nullable FK to `TenantPerson`, partial unique `(org, company, person) WHERE person_id NOT NULL`, FK `(org, person) -> (org, id)` | Durable person/company relationship preserving IDs | `CompanyContact.id` already targeted by method/investigation/outreach/qualification | Identity must not churn contact IDs or outreach history breaks | Composite FK guarantees same tenant; tenant reassignment forbidden | Duplicate `(org, company, person)` via DB unique; cross-tenant person_id -> 403 | Existing `first_name/last_name/full_name/job_title` become compatibility projections; not separately writable after mapping | Add column nullable; old rows NULL = unmapped; mapped only after review | Existence+unique violation; NULL rows render unmapped | Alt: new join table -> rejected (churn) |
| 3 | **ContactEmployment (new)** — `id, org, company, contact, start_date, end_date, status CURRENT/FORMER/UNKNOWN`, partial unique `CURRENT` per contact | Model current/former, rehire, UNKNOWN dates | No employment history; current row implicit | Need episodes for authority timing and rehires | FK `(org, company, contact)` validated | Only one `CURRENT` per contact; competing CURRENT -> review queue | Per-employment evidence; future observed date -> 422 | Additive; legacy row preserved as episode only if dates known else UNKNOWN | UNKNOWN, ordering, CURRENT uniqueness, rehire tests | Alt: infer from updated_at -> rejected |
| 4 | **ContactProfessionalRole (new)** — `id, employment_id, org, company, title/dept/seniority/geography/authority DECISION_MAKER/INFLUENCER/UNKNOWN`, concurrent roles allowed | Distinguish title from buying authority | `ContactSeniority` + `DecisionLevel` enums flat | Title alone must not prove authority | Linked to `ContactEmployment`, same tenant/company | Multiple roles per employment allowed; authority per role | Per-role evidence; authority requires source | Additive; legacy DecisionMaker maps after review only | Multi-role overlap, UNKNOWN without evidence | Alt: single role column -> insufficient |


### 2.1 Per-proposed-change analysis (2 of 2)

| # | Proposal | Business need | Existing reusable | Why necessary | Tenant isolation | Duplicate / ambiguous | Evidence / provenance | Migration / back-compat | Test strategy | Alternatives |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | **Person/Employment/Role evidence (new)** — typed `target_id` FK to specific parent | Immutable provenance, correction by superseding | No immutable field-level history; `ContactInvestigation` single mutable row | Verified claims must be append-only | Must carry `org`, direct FK to correct parent (no generic polymorphic key) | Generic polymorphic key would let row point to any tenant's record | FACT/INFERENCE/UNKNOWN, review status, actor/time immutable after VERIFIED; `confidence` NULL without ratified formula | Seed legacy as UNVERIFIED/UNKNOWN only; verified after human review | Immutability (verified -> 409), freshness per assertion | Alt: reuse f5_evidence_claims -> rejected |
| 6 | **CompanyContactMethod reuse** — no duplication | Display verified methods read-only | Methods scoped to `contact_id` with uniqueness | F7 must not re-verify or re-acquire details | Methods relationship-scoped; address never propagates | Repeated value for same canonical contact reuses one method; uncertain shared address -> review | F8 owns acquisition/normalization/freshness | No method schema change; F8 extends same IDs | Duplicate across persons same tenant/company -> 409 or REVIEW | Alt: new person-level methods -> rejected |
| 7 | **Legacy DecisionMaker adapter** — `legacy_decision_maker_mapping(legacy_id UNIQUE, contact_id, employment_id)` | Preserve commercial Lead/Activity links | `DecisionMaker.id` referenced by Lead/Activity | Cannot drop; pipeline loses FK | Mapping same-tenant/company only | Many legacy IDs -> one contact after resolution; both histories retained | Legacy fields projected; edits go through canonical service same tx | No cascade delete; rollback retains history | Adapter projection + rollback fixture | Alt: migrate FKs directly -> destructive |

### 2.2 Cross-cutting proposal risks confirmed

- **Verification-role dilution:** Proposal says “verification uses explicitly authorized human write roles initially.” Verified — currently `require_organization_write` allows MEMBER. Owner must decide whether verification should require MANAGER+ or OWNER/ADMIN only (separation-of-duties).
- **Confidence numeric:** Proposal correctly keeps `confidence` NULL unless ratified. Do NOT invent a score.
- **Cross-tenant leakage:** No global directory, no global email uniqueness, no cross-tenant duplicate hints, no automatic evidence propagation — as proposed and required.
- **Freshness thresholds:** `FRESH <=90, AGING 91-365, STALE >365, UNKNOWN` are **proposed for employment/role**, not ratified business truth. Implement as explicit function (`freshness_for_dates`) and label thresholds configurable.
- **Compatibility writes:** “Retain old response shapes and IDs, update projections in same transaction. No dual writes” — ratify; dual writes diverge under concurrency.



## 3. Business workflow — identity ambiguity stays visible

```
Company (tenant-owned, organization_id)
  └─ CompanyContact (organization_id, company_id) — durable relationship, keeps its id
       ├─ person_id → TenantPerson (organization_id, id) — ONE human per tenant
       │    └─ evidence: name/lifecycle assertions (source, observed_at, evidence_date, FACT/INFERENCE/UNKNOWN, review_status, verifier/time, superseded_by)
       ├─ CompanyContactMethod (per relationship, verification_status) — F8-owned, F7 read-only
       ├─ ContactEmployment (per relationship, CURRENT/FORMER/UNKNOWN + dates) — one CURRENT per contact max
       │    ├─ employment evidence (same shape)
       │    └─ ContactProfessionalRole (title/department/seniority/geography/authority DECISION_MAKER/INFLUENCER/UNKNOWN)
       │         └─ role/authority evidence (separate source needed; title ≠ authority)
       ├─ ContactInvestigation (legacy, 1 row/contact, booleans) — preserved as legacy fact
       ├─ ContactOutreachActivity / ResponseQualificationAssessment — preserved
       └─ LegacyDecisionMakerMapping — keeps Lead/Activity FK history
```

**Workflow (human-controlled, no automatic side effects):**

1. **Company** exists. Cannot attach person without validated `Company.organization_id`.
2. **Possible person** created with `display_name` only; optional `source_namespace/external_id` attached *only after* review (unique `(org, namespace, external_id)`).
3. **Verified identity** after reviewer verifies evidence (`source/source_url/observed_at/evidence_date/classification/verifier/verified_at`). Verified row immutable; correction = new superseding row.
4. **Employment episode** links person↔company with `start_date/end_date/status`; only one `CURRENT` per contact; competing `CURRENT` quarantined.
5. **Decision-maker role** within employment with title/department/seniority/geography and authority; multiple concurrent roles allowed; authority per role needs own evidence.
6. **Contact methods** remain on `CompanyContact`; F7 displays read-only; F8 owns verification/provenance; method duplication across persons in same `(org, company)` conflicts.
7. Identity ambiguity (similar names, shared mailbox) stays visible as `POSSIBLE_DUPLICATE / REVIEW_REQUIRED`; demand side never treated as bulk resolved. **No auto lead/requirement/opportunity/deal/outreach** as side effect of discovery.

Any “verified contact” optimism is out-of-scope until F8. F7 never infers employment from a phone/email value.



## 4. Security and data-integrity acceptance (all must be demonstrable before DONE)

| # | Requirement | Acceptance criterion (objective) | How it will be proved |
|---|---|---|---|
| S1 | Org-scoped reads/writes | Every F7 list/detail/mutation requires explicit `organization_id` (query/body) with ACTIVE membership (or explicit org context for global admin). Unscoped list → 400/422, no silent enumeration. | API tests with missing org → 422; correct org → 200. Follows F5 precedent rejecting global admin without `organization_id`. |
| S2 | Company ownership check | `Company.organization_id == organization_id` verified for every person/company/employment/role create; mismatch → 403 with tenant-safe message. | Cross-company fixture: create person in Org A, attempt link to Org B company → 403, no existence oracle. |
| S3 | Identity uniqueness + concurrency | `tenant_person_source_keys` unique `(org, namespace, external_id)` WHERE not null; `company_contacts` partial unique `(org, company, person)` WHERE `person_id` not null; `contact_employment` partial unique `CURRENT` per `contact_id`. Concurrent duplicate creates via 2 PG transactions → one 201, one 409 (`IntegrityError` handled). | PG concurrency harness (row-lock/idempotent/unique) mirroring `postgres-concurrency.json` pattern from F6. Service-level duplicate scan alone is insufficient. |
| S4 | Ambiguous matches | Similar names (e.g., `Pvt Ltd` normalized vs `Private Limited` — `normalize_company_name` precedent), email similarity, shared mailbox **never** auto-merge. Flagged `POSSIBLE_DUPLICATE`/`REVIEW_REQUIRED`; canonical promotion requires explicit `resolve` with evidence. | Tests: same normalized name → still separate until `resolve`; shared method value across two persons same `(org, company)` → 409 or queued review, not propagated identity. |
| S5 | Evidence provenance | Every assertion stores `source/source_url/observed_at/evidence_date/classification/review_status/recorder/reviewer/verifier/verified_at/superseded_by_id`. `VERIFIED` rows immutable (409 on direct edit); correction via new superseding row retaining original. `confidence` NULL unless ratified. | Evidence integrity suite: verify transition `UNVERIFIED→VERIFIED` records actor/time; attempt edit verified → 409; `superseded_by` chain preserved. |
| S6 | Freshness (proposed thresholds) | Per-assertion `freshness_for_dates(observed_at, evidence_date)` → FRESH ≤90d / AGING 91-365d / STALE >365d / UNKNOWN (no date), using newest date. Viewing/editing profile never refreshes dates; `last_verified_at` is separate from `evidence_date`. | Boundary tests at 90d/91d/365d/366d + UNKNOWN null case; prove no side-effect on profile read. Thresholds labeled configurable, not approved business truth. |
| S7 | Contact-method verification | F7 is read-only for methods (reuse `CompanyContactMethod.verification_status`); F8 owns acquisition/normalization/provenance/freshness/primary selection. Method address verification never propagates to another employment/company. | F7 tests show method read via `CompanyContact` but no F7 write; F8 reuse check: same canonical method reused for same person, not duplicated. |
| S8 | Account / membership boundaries | VIEWER denied on every mutation (POST/PATCH/verify/resolve) → 403. Revoked membership/token_version increment effective immediately on next request (no restart needed). | Tests: VIEWER fixtures for each mutation; deactivate membership mid-session → next F7 request 403 (uses `get_active_membership` + `token_version`). |
| S9 | Migration & rollback safety | Additive tables + nullable FK only; dry-run inventory first; no customer backfill without authorized rehearsal; rollback disables routes/UI, retains tables/history/mapping snapshot, forward corrective migration preferred over downgrade in production. | Disposable PG rehearsals: upgrade→downgrade→re-upgrade with row counts + unicode alias preservation (as F6 `verify_f6_migrations` pattern); rollback fixture: `Lead/Activity` FKs intact after disabling F7 routes. |
| S10 | API error contracts | Consistent JSON `{"detail": string, "code": string}` (code: `forbidden/access_denied`, `not_found`, `conflict/duplicate`, `validation_error`, `verification_forbidden`); correct HTTP 401/403/404/409/422; no token/secret leakage. | Contract tests for each code; redaction audit (no `SECRET_KEY` samples in logs). |
| S11 | Human-controlled resolution | No silent merges; ambiguous rows stay `REVIEW_REQUIRED` until `POST /resolve` with evidence and verifier; promotion idempotent; `hr_history` preserved. | Browser + API: unresolved row visible as conflict chip, resolve requires evidence payload; competing `CURRENT` stays quarantined. |
| S12 | Frontend states | Loading, empty, conflict/review, 401/403/404/network distinctive; stale-response discard via `requestId` guard (route delay 600ms) as in `RequirementIntelligencePage`. | Browser stale test: `page.route` delay 600ms on Org A, switch A→B → B wins after 800ms (reuse F6 `requirement-organization-b-no-stale-a` pattern). |



## 5. Recommended F7 scope (implementation-ready, ratification-gated)

### 5.1 Scope and explicit non-goals

**In:** Tenant-scoped person CRUD, employment/role CRUD + append-only history, typed immutable evidence with review lifecycle, duplicate/conflict review queue, manual entry/edit, list/detail with server-side search + bounded pagination, derived freshness chips, verified-data protection (verified → 409 on silent edit), tenant-isolation and membership checks on every request.

**Out:** Scraping, enrichment executors, contact-method acquisition/normalization/verification (that's F8), reminders/outreach, automatic lead/deal/opportunity/requirement creation, scoring/promotion, commercial-status mutation, global dedup, bulk import without review, and any unscoped enumeration. Existing `decision-makers` / `company-intelligence` / `contact_workflow` / `response_qualification` features remain **read-compat** consumers, never F7 actions.

### 5.2 Existing capabilities to reuse (do not re-invent)

`Organization`/`Company`/`User`/`OrganizationMembership`, `DecisionMaker` (compat), `CompanyContact`/`CompanyContactMethod`/`F5CompanyProfile`/`RequirementIntelligenceEvidence`, `ContactInvestigation`/`ContactOutreachActivity`/`ResponseQualificationAssessment`, `organization_access` helpers (`require_organization_access/write`, `is_global_admin`), `freshness_for_dates`, `normalize_company_name`, Frontend `ApiError`/`organizationContext`/`useOrganizationWrite`/debounce + stale guard / `F5CompaniesPage` pagination ordering. Follow `DATABASE_DESIGN.md` conventions (`_enum_type`, `_json_type`, `CheckConstraint`, `Index` with `sqlite_where`/`postgresql_where`, composite FKs).

### 5.3 Proposed data-model changes (additive, tenant-consistent — only if ratified)

```
TenantPerson {
  id PK, organization_id FK→organizations.id CASCADE NOT NULL,
  display_name String(255) NOT NULL, lifecycle ACTIVE/ARCHIVED DEFAULT ACTIVE,
  created_by_user_id FK→users.id SET NULL, created_at/updated_at,
  UNIQUE(organization_id, id)  -- enables child FK (org, person_id)
}
TenantPersonSourceKey { org, person_id FK CASCADE, namespace, external_id,
  UNIQUE(org, namespace, external_id) }
CompanyContact.person_id  -- ALTER ADD nullable
  FK (org, person_id) → TenantPerson(org, id)
  partial UNIQUE(org, company, person) WHERE person_id IS NOT NULL
ContactEmployment {
  id PK, org, company_id, contact_id, person_id (derived),
  start_date, end_date, status CURRENT/FORMER/UNKNOWN,
  partial UNIQUE(contact_id) WHERE status='CURRENT'
  CHECK(end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
}
ContactProfessionalRole {
  id PK, employment_id FK CASCADE, org, company,
  title, department, seniority, geography, responsibility,
  authority DECISION_MAKER/INFLUENCER/UNKNOWN DEFAULT UNKNOWN
}
Person/Employment/RoleEvidence (three tables, same shape) {
  id PK, org, target_id FK→specific parent CASCADE,
  field_or_assertion, source, source_url, observed_at, evidence_date,
  classification FACT/INFERENCE/UNKNOWN, review_status UNVERIFIED/REVIEWED/VERIFIED/REJECTED,
  recorder/reviewer/verifier ids + verified_at, superseded_by_id FK self,
  confidence Numeric 0..1 nullable (stays NULL without ratified formula)
}
LegacyDecisionMakerMapping {
  legacy_decision_maker_id PK/FK→decision_makers.id UNIQUE,
  contact_id FK→company_contacts.id, employment_id nullable, resolved_at/by
}
```

**Tenant consistency rule:** Every new child carries `organization_id` (and `company_id` where company-scoped); service + DB enforce `child.org == parent.org == Company.org` via composite FKs. Never mutate `organization_id` after creation; moving jobs → new `ContactEmployment` row. Mirrors `F5CompanyProfile`'s `UniqueConstraint(org, company)` boundary.



### 5.4 Migration sequence + compatibility strategy

1. **Inventory (read-only):** Script counts per `(org, company)` the `CompanyContact`, `CompanyContactMethod`, `ContactInvestigation`, `DecisionMaker`, `Lead`/`Activity` refs, normalized name collisions, method collisions; outputs dry-run mapping/conflict list. **No customer backfill authorized by this document.**
2. **Additive migration y1 (F7 data layer):** Create `tenant_persons`, `tenant_person_source_keys`, `contact_employments`, `contact_professional_roles`, `*_evidence`, `legacy_decision_maker_mapping`; add `company_contacts.person_id` nullable. No column dropped, no FK removed.
3. **Synthetic rehearsal:** Disposable PG (`bwip_followup_+12hex` pattern) with synthetic fixtures (2 orgs, 3 companies, 6 persons, method collisions, similar names). **No `bwip_db` writes.**
4. **Service compatibility adapter:** Single canonical service routes both legacy `DecisionMaker` reads/writes and F7 `TenantPerson/CompanyContact` mutations in SAME transaction; old shapes retained; `first_name/last_name/full_name/job_title` become projections of canonical person+employment; no dual writes.
5. **Y1 verification:** Upgrade head → downgrade to `w8`/`x9` → re-upgrade on disposable PG; assert schema equality, row counts, unicode alias preservation, single head — as in `scripts/verify_f6_migrations.py`.
6. **Customer enablement (gated):** Only after synthetic + **authorized** capture/restore rehearsal in isolated env with owner approval; unresolved legacy rows remain `person_id NULL = unmapped` until next edit requires resolution.
7. **Y2 (post-F7):** Optional backfill mapping for authorized tenant after review resolution, with rollback snapshot preserved; never auto-merge; forward correction only.

**Rollback:** Disable F7 UI/routes (`/f7/*`, `/people`), keep additive tables + mapping/history + forward snapshot, restore adapter. Do NOT drop person/evidence tables or reverse committed merges; if canonical writes cannot be represented by old build, hold identity mutations read-only until corrected. Prove with real FK/history fixtures before release.



### 5.5 Backend service / API (proposed — reuse conventions)

- `GET /f7/people?organization_id=&search=&company_id=&has_current_employment=&freshness=&page=&page_size=` → `{ items:[{ id, display_name, org, lifecycle, current_employment, roles, freshness, duplicate_status }], total, page, page_size }`. Server ilike on display_name/company/department/seniority; `freshness` bucket filter; deterministic order `display_name, id`; bounded `page_size` default 25 max 100; stale guard via `requestId`.
- `POST /f7/people` `{ org, display_name, source_key?:{namespace,external_id}, idempotency_key }` → 201; duplicate source_key → 409; wrong org or VIEWER → 403; requires `require_organization_write`.
- `GET /f7/people/{id}?organization_id=` + `PATCH /f7/people/{id}` (display_name/lifecycle) + `GET /f7/people/{id}/history` (evidence + status timeline, monotonic `created_at`).
- `POST /f7/companies/{company_id}/contacts` `{ org, person_id }` — link person to company via existing `CompanyContact.id`; duplicate `(org, company, person)` → 409; rehire reuses contact with new employment episode, not new contact.
- `POST /f7/contacts/{contact_id}/employments`, `PATCH /f7/employments/{id}`, `POST /f7/employments/{id}/roles`, `PATCH /f7/roles/{id}` — all require `organization_id` + write role + company ownership; `CURRENT` uniqueness enforced at DB.
- Evidence: `POST /f7/people/{id}/evidence`, `/f7/employments/{id}/evidence`, `/f7/roles/{id}/evidence` with `source/source_url/observed_at/evidence_date/classification/field`; transitions `POST /f7/evidence/{id}/review { action: VERIFY|REJECT|SUPERSEDE }` recording verifier/verified_at; verified → 409 on direct PATCH; `SUPERSEDE` requires new row.
- Resolve: `POST /f7/duplicates/{id}/resolve { target_person_id, evidence }` + `POST /f7/duplicates/{id}/quarantine`.
- Legacy compat: `GET /decision-makers/company/{companyId}` and `/companies/{id}/intelligence` continue via canonical projection; legacy `POST /decision-makers/` adapted to canonical service in same tx where supported.
- Errors: `{"detail": str, "code": "validation_error|forbidden|not_found|conflict|duplicate|verification_forbidden"}`; 401/403/404/409/422 correctly; no secret leakage; unscoped `organization_id` → 422.

### 5.6 Frontend workflow (proposed)

- **People list** `/people` (new nav: Companies → People, as in `Sidebar.tsx` placeholder): org picker (first active org for MEMBER, explicit picker for ADMIN), search, company filter, pagination, freshness chips, duplicate-review tab; reuses debounce 180ms + requestId stale-discard + `waitForListStable` + record-count + card classes.
- **Person detail** `/people/:id`: header + employment timeline + roles table + evidence cards (source/classification/freshness/verified_by/at) + immutable history; review controls gated by `useOrganizationWrite`; conflicts shown side-by-side; no auto-merge CTA.
- **Company context** `/companies/:id` tab “People linked”: linked people + “Add existing person” (search `GET /f7/people?search=`) + “Create new person” requiring evidence before link; uses `POST /f7/companies/{id}/contacts`.
- **States:** Loading skeleton, Empty (no people/evidence), Conflict (review required), 403/401/404 distinctive, network retry — reuse `EmptyState` + `ApiError.kind`. No method acquisition/verification fab, no outreach CTAs, no conversion triggers in F7 UI.



### 5.7–5.10 Tests and browser QA (proposed)

- **5.7 Security + isolation:** member of A cannot read/write B; viewer 403 on every mutation; global admin without `organization_id` → 422; cross-tenant `person_id` → 403; revocation mid-session → 403 on next request (token_version path).
- **5.8 Ambiguity + concurrency:** concurrent same source key → 1×201 + 1×409 via DB unique; similar normalized names stay separate until resolve; shared mailbox same `(org, company)` → 409 or REVIEW_REQUIRED; rehire close/reopen preserves both episodes.
- **5.9 Evidence integrity:** UNVERIFIED→VERIFIED records verifier/time; verified PATCH → 409; supersede retains original; freshness at 90/91/365/366 + UNKNOWN; future observed → 422; legacy booleans stay UNVERIFIED/UNKNOWN.
- **5.10 Browser QA (disposable PG, as F6):** List/search/pagination without stale (2 orgs, 2–3 persons, `page.route` 600ms delay, A→B discard); detail+review flow (create→employment→role→evidence→verify→immutability→viewer read-only); conflict display (duplicate → review queue, manual resolve, history).

### 5.11 F7.1–F7.6 acceptance matrix (PROPOSED, not yet PASS — do not claim green)

| Check | Objective pass condition | Signal of PASS |
|---|---|---|
| F7.1 CRUD+history | Same-tenant person/employment/role CRUD round-trips; `GET /history` monotonic; UNKNOWN dates/authority explicit; multi-role + rehire preserved | Disposable PG API suite PASS |
| F7.2 Membership/isolation | VIEWER denied every mutation; wrong-tenant IDs/joins/methods → 403/404; revocation immediate; delayed UI responses discarded | Security suite + browser stale tests PASS |
| F7.3 Provenance/verification | True actor/time/source dates; verified immutable; freshness per-assertion at boundaries; legacy flags not treated as verified | Evidence integrity suite PASS |
| F7.4 Duplicates/concurrency | Concurrent duplicate source/link → one canonical + 409; similar names/shared mailbox separate until explicit resolution | PG concurrency harness PASS |
| F7.5 Legacy/rollback | `Lead.primary_decision_maker_id` + `LeadActivity.decision_maker_id` + investigation/method/qualification intact after y1 and after disabling F7 routes | Migration rehearsal + rollback fixture PASS |
| F7.6 Browser + F8 boundary | Real browser list/detail/reload/org-switch/read-only at desktop/tablet/mobile against disposable API/UI PASS; F8 reuses methods without duplicate person/contact | F7 browser suite PASS |

### 5.12 Dependencies, risks, rollback

- **Depends on:** PostgreSQL disposable rehearsal infra (`disposable_database(bwip_followup_+12hex)` / `verify_followup_runtime`), `token_version` + `rate_limit_buckets` (`w8`), `Company.organization_id` ownership, `ApiError`/`useOrganizationWrite` conventions.
- **Top risks:** (1) Over-modeling person vs contact-as-identity → mitigated by additive `person_id`; (2) Global dedup temptation → forbidden; (3) Service-only duplicate check race → must add DB uniques; (4) Invented confidence → must stay NULL; (5) Dual writes diverging → single canonical service.
- **Rollback risk:** If old build cannot represent new canonical writes, hold identity mutations read-only until forward fix; never auto-downgrade committed history.



### 5.13 Phased implementation sequence + Definition of Done (proposed order)

- **Phase A — Ratification (this report):** Owner approves the decisions in §6; no code runs. Gate: explicit written approval recorded.
- **Phase B — Data layer (y1):** Inventory script + additive migration + disposable PG upgrade/downgrade/re-upgrade + concurrency/evidence unit tests. No UI/routes yet. Gate: migration chain single-head, history intact, `SELECT LIKE 'bwip_followup_%'=0`.
- **Phase C — Service / API:** Canonical service + `/f7/*` routes + pagination/filters + security/isolation/evidence tests on disposable PG. Gate: S1–S11 suites PASS with synthetic fixtures only.
- **Phase D — UI:** List/detail/review workflows + loading/empty/conflict/error/stale states + company tab. Gate: component + integration tests PASS.
- **Phase E — Disposable rehearsal closure (as F6 did):** Full `verify_followup_runtime`-equivalent with 2 uvicorn + Vite + Playwright (`qa.e2e.ts` + new `f7.e2e.ts`) proving F7.1–7.6 on disposable PG; backup/restore rehearsal; evidence JSON under `docs/development/evidence/`. Gate: `browser-results.json` expected count increments by exactly F7 tests, no new unexplained failures; `sessions/distributed-rate-limits/backup-restore/postgres-concurrency`-equivalent PASS.

**Definition of Done:** All F7.1–F7.6 objective checks PASS on **disposable PostgreSQL** (never `bwip_db`); no unscoped reads; verified rows immutable; duplicates quarantined not auto-merged; migration head single and additive; legacy FKs intact; browser stale + read-only + F8 no-duplicate evidence preserved; all prior audit reports preserved; no `SECRET_KEY` samples or placeholder DB credentials in evidence. F8 Contact Verification explicitly deferred unless the minimum method-display interface (F7 read-only reuse of existing method) is ratified.

F8 interface (minimum, proposed): F7 exposes `GET /f7/contacts/{id}/methods` (read-only projection of existing `CompanyContactMethod` rows). F8 owns `POST/PATCH /f8/contacts/{id}/methods` + verification/provenance/freshness/primary selection; no second person import.

### 5.14 What F7 must NOT do

- Do not create leads/requirements/opportunities/deals/outreach as side effect of discovery.
- Do not scrape, enrich, or exec enrichment jobs.
- Do not infer employment from a contact method value.
- Do not refresh freshness by viewing/editing a profile.
- Do not store cross-tenant duplicate hints or global email index.
- Do not run `alembic downgrade` as production rollback.
- Do not begin F8 until §6 decisions are ratified or the minimum read-only method interface above is approved.

### 5.15 Traceability to source requirements

| Requirement source | Section in this plan |
|---|---|
| `docs/product/PRD.md` “Decision Maker Intelligence — Identify key decision-makers, maintain verified contact, track hierarchy” + `docs/ROADMAP.md` Phase 2 CRM Foundation (Company/Decision maker management) + `docs/product/ROADMAP.md` v0.3 CRM (Company/Contact/Lead/Opportunity/Follow-up) + Success Metrics (occupancy/conversion) | Reinterpreted as F7 human-verified identity/employment/role + evidence, without outreach auto-creation |
| `docs/architecture/DATABASE_DESIGN.md` draft §4.4/§11.2 envisaging `decision_makers` as sole person | Amended explicitly: keep `decision_makers` as legacy mapping, promote `CompanyContact` as durable relationship, add `TenantPerson` as canonical identity |
| `docs/architecture/F5_COMPATIBILITY_BOUNDARY.md` additive boundary, namespaced `/f5`, tenant-consistent FKs | Mirrored for F7: additive `/f7`, tenant-consistent `(org, id)` pattern, compatibility adapter, no dual writes |



## 6. Decisions requiring owner approval (do NOT infer)

| # | Decision | Why it matters | Alternatives | Consequence of each | Recommendation |
|---|---|---|---|---|---|
| D1 | **Person scale: tenant-local vs global directory** | Tenant boundary determines cross-tenant leak surface and GDPR/DPDP handling | A) Tenant-local (proposed) B) Global person with cross-tenant dedup C) Per-company only | A) Minimal leak, no hints, explicit per-tenant work B) Global index + hints → leak + bulk merge risk C) Duplicate persons, no rehire model | **A — tenant-local.** Ratified by proposal; do not build B. |
| D2 | **Freshness thresholds for employment/role evidence** | Determines “stale authority” UX and SLA messaging | A) Reuse F5 `90/365` (proposed) B) Shorter (30/90) C) Longer (180/730) D) Per-field configurable | Affects when stale banner shows; B shows stale quickly; C hides staleness; D adds config complexity | **A as starting point, label thresholds configurable** and log the approved values. |
| D3 | **Verification role / separation-of-duties** | Who can mint “verified decision-maker” | A) Any MEMBER can verify (current `require_organization_write`) B) MANAGER+ only C) OWNER/ADMIN only + optional maker/checker | A) Low friction but dilution; B/C) higher authority assurance but staffing constraint | **B minimum (MANAGER+) for VERIFY/REJECT**, OWNER/ADMIN for `resolve`; record choice. |
| D4 | **Legacy DecisionMaker fate** | Commercial pipeline FK safety and audit trail | A) Preserve as compatibility projection (proposed) B) Migrate FKs to `CompanyContact` eagerly C) Dual-write both | A) Safe rollback; B) Destructive if wrong; C) Divergence risk | **A — preserve + mapping table + single canonical service.** |
| D5 | **Method ownership boundary** | Whether F7 can create/verify methods | A) F7 read-only (proposed) B) F7 can verify lightweight methods | A) Clean F8 separation; B) Blurs provenance ownership | **A — reuse existing methods read-only; F8 owns verification.** |
| D6 | **Source-identity key semantics** | How external identity linkage is gated | A) `source_namespace/external_id` attached only after reviewed evidence (proposed) B) Auto-attach on any import C) No keys, name-only | A) Proof-gated; B) Silent merges on colliding external_id; C) No stable linkage for re-imports | **A — review-gated attachment.** |
| D7 | **Duplicate resolution UX** | Prevents silent bulk merges | A) Explicit per-record `resolve`/`quarantine` with evidence (proposed) B) Bulk “merge all similar names” | A) Human control; B) High false-merge harm | **A — no bulk merge.** |
| D8 | **Contact name/title field semantics after mapping** | Avoids competing writable facts | A) Become projections (proposed) B) Keep independently writable | A) Single source; B) Divergent display_name vs contact name | **A — projections, single transaction.** |
| D9 | **Customer backfill authorization** | Production data risk | A) Synthetic-only until authorized isolated rehearsal passes (proposed) B) Immediate backfill | A) Safe; B) Merges real tenant data without review | **A — no customer backfill without isolated capture/restore rehearsal + owner sign-off.** |
| D10 | **Evidence model shape** | Tenant isolation + FK correctness | A) Typed tables per parent with direct FK (proposed) B) Single polymorphic `evidence(target_type,target_id)` | A) Tenant FK verifiable; B) Generic FK defeats tenant join checks | **A — typed evidence tables.** |

Owner ratification must be **explicit and recorded** before any Phase B work begins. Do not claim it has occurred.
