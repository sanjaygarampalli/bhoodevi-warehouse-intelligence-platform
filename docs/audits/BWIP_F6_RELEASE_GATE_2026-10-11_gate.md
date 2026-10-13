# BWIP F6 Release-Gate Verification - 2026-10-11T21:55 Asia/Calcutta

**Scope:** F6 Requirement Intelligence only. Bounded, non-destructive verification. No F7, no auth/DB mutation, no git reset/clean/commit/push.

## 1. Repository baseline

- **Working dir:** E:\\BHOODEVI-Warehouse-Intelligence-Platform (verified)
- **Branch:** feature/company-module
- **HEAD:** a32bf6b03a174c4a046df75538ddca8c75bbe5f0 (docs: freeze backend API contract baseline)
- **Log -5:** a32bf6b docs: freeze backend API contract baseline | 1942267 fix: install test client dependency in CI | 15fb034 fix: install pytest in CI | ca035a5 fix: correct prospect prioritization f-string syntax | 50a8cce feat: complete warehouse intelligence backend foundation
- **git status --short (pre-existing, preserved):**
  - M (39 tracked): .github/workflows/validation.yml, .gitignore, README.md, alembic/env.py, app/api/v1/endpoints/{auth,deal_pipeline_stage,lead,operational_dashboard,organization,requirement_candidate_conversion,warehouse,warehouse_intelligence_conversion,warehouse_match}, app/api/v1/routes.py, app/core/{config,security}, app/dependencies.py, app/main.py, app/models/{__init__,requirement,user}, app/repositories/{requirement_candidate_conversion,warehouse_intelligence_conversion,warehouse_match}, app/schemas/user.py, app/services/{deal,decision_maker_relevance,requirement_candidate_conversion,response_qualification}, docs/{RELEASE_READINESS,api/API_CONTRACT,operations/{BACKUP_AND_RECOVERY,DEPLOYMENT}}, requirements.txt, tests/{test_config,test_deal,test_end_to_end_workflow,test_opportunity_workflow,test_organization_access,test_requirement_candidate_conversion,test_warehouse_matching_engine,test_warehouse_matching_intelligence}
  - ?? (untracked, preserved): .qa_baseline.txt, .qa_f5page.txt, .qa_fe_tree.txt, alembic/versions/{s4e5f6a7b8c9_add_f5_company_intelligence.py,t5e6f7a8b9c0_add_requirement_intelligence.py,u6f7a8b9c0d1_align_pilot_snapshot_jsonb.py,v7a8b9c0d1e2_align_intelligence_jsonb.py,w8b9c0d1e2f3_session_revocation_rate_limits.py,x9c0d1e2f3a4_google_sign_in.py}, app/api/v1/endpoints/{f5_company_intelligence.py,requirement_intelligence.py}, app/core/rate_limit.py, app/models/{f5_company_intelligence.py,google_login_challenge.py,rate_limit.py,requirement_intelligence.py}, app/schemas/{f5_company_intelligence.py,requirement_intelligence.py}, app/services/{f5_company_intelligence.py,google_auth.py,requirement_intelligence.py}, docs/{architecture/F5_COMPATIBILITY_BOUNDARY.md,audits/,development/,frontend/,scripts/}, tests/{conftest.py,test_auth_rate_limit.py,test_browser_transport.py,test_company_detail_acceptance.py,test_f5_company_intelligence.py,test_google_auth.py,test_requirement_intelligence.py,test_security_audit.py,test_session_revocation.py}
- **Preservation:** No reset/clean/commit/push; no code or migration changed during gate.

## 2. Exact commands executed and exit codes

| # | Command | Exit |
|---|---|---|
| 1 | git rev-parse HEAD | 0 - a32bf6b03... |
| 2 | git branch --show-current | 0 - feature/company-module |
| 3 | git log --oneline -5 | 0 |
| 4 | git status --short | 0 |
| 5 | .venv\\Scripts\\python.exe -m pytest tests/test_requirement_intelligence.py -q --tb=short --disable-warnings | 0 |
| 6 | cmd /c cd frontend && npm.cmd run typecheck | 0 |
| 7 | cmd /c cd frontend && npm.cmd run build | 0 - vite 7.3.6, 59 modules, 4.52s |
| 8 | cmd /c cd frontend && npm.cmd test | 0 |
| 9 | .venv\\Scripts\\python.exe -c (config isolation check with SECRET_KEY synthetic) | 1 without key (expected fails-closed), 0 with synthetic key |
| 10 | read_files inspections (F6 routes/schemas/services/models/frontend) | 0 - all 4 F6 layers inspected |

No full backend suite, no destructive alembic upgrade/downgrade, no shared-DB integration was executed per Rules 5 and Do-not-start-full-suite.

## 3. F6 code inspection (read, not modified)

**Routes (app/api/v1/endpoints/requirement_intelligence.py):** APIRouter /requirement-intelligence with 6 endpoints: GET /?organization_id (Query gt0, optional status/query/limit 1-100/offset), GET /{id}, GET /{id}/assessment, GET /{id}/evidence, POST /{id}/evidence (201, RequirementEvidenceConflict->409), PATCH /{id}/evidence/{evidenceId}. All detail/mutate paths use scoped_requirement -> require_organization_access; POST/PATCH additionally require_organization_write. Verified.

**Schemas (app/schemas/requirement_intelligence.py):** RequirementEvidenceInput (extra forbid, str_strip_whitespace) normalizes evidence_date: tz->UTC naïve, rejects future dates via datetime.now(timezone.utc). RequirementEvidenceCreate requires source(1-255)/observed_evidence/classification, defaults verification_status UNVERIFIED, confidence 0-100. RequirementEvidenceUpdate rejects explicit null for source/observed_evidence/classification/verification_status via model_validator. Assessment/Intelligence response models include freshness/reasons/evidence_strength.

**Service (app/services/requirement_intelligence.py):** organization_id() via Company<-Lead<-Requirement join; list_requirements filters by organization_id + optional status/query; company_for validates FK; evidence ordered by evidence_date desc nullslast; create_evidence rejects VERIFIED on create (must be reviewed); update_evidence enforces REVIEWED->VERIFIED gate and immutability of VERIFIED (409); assessment computes freshness (UNKNOWN if no anchor, STALE >90d via 2020-01-01 test), dimensions confidence nulled intentionally (field presence != proof), evidence_strength = verified/len *100, live GET returns non-persisted RequirementAssessmentResponse(id=None). market_signal_ids follows RequirementCandidateConversion CONVERTED only, same org, distinct - never company identity. No env or global state.

**Models (app/models/requirement_intelligence.py):** RequirementEvidenceClassification FACT/INFERENCE/UNKNOWN; Verification UNVERIFIED/REVIEWED/VERIFIED/REJECTED; Freshness FRESH/AGING/STALE/UNKNOWN. Tables requirement_intelligence_evidence (FK organizations.id/requirements.id/users.id, indexes on requirement_id/organization_id) and requirement_intelligence_assessments (unique requirement_id, JSON reasons). Both use server_default func.now().

**Migration (alembic/versions/t5e6f7a8b9c0_add_requirement_intelligence.py):** Creates 3 PG ENUMs (checkfirst) and both tables with indexes; downgrade drops indexes/tables/enums. Inspected only - not executed against live DB.

**Frontend API (frontend/src/api/requirementIntelligence.ts):** listRequirementIntelligence(organization_id, query, status) builds URLSearchParams, getRequirementIntelligence(id), listWarehouseMatches(requirement_id), convertWarehouseMatch. All via apiRequest with explicit organization_id param.

**Frontend page (frontend/src/pages/RequirementIntelligencePage.tsx):** List/detail via useEffect with getAuthenticatedContext (single-org auto-select, multi-org selector), 180ms debounce, stale-guard active flag + clearTimeout, errorTitle maps 401/403/404/network, KPI grid (total/needsVerification/highConfidence/stale), search/status filters, EmptyState, SectionHeader, RequirementEvidenceControls integration. Detail: MatchCard with convertWarehouseMatch (confirm, stage_id validation, 409 handling), EvidenceCard shows classification/source/verification_status/evidence_date/confidence.

**Evidence controls (frontend/src/components/RequirementEvidenceControls.tsx):** Loads canWrite via getAuthenticatedContext (admin or MEMBER/OWNER/ADMIN/MANAGER), form with source/observed/inference/classification/source_url/evidence_date(datetime-local->ISO), POST as UNVERIFIED, then REVIEWED->VERIFIED with confirm dialogs, REJECTED with provenance retention note. Busy/submitting guard.

No code changed to make tests pass.

## 4. Test results

**Focused F6 suite:** pytest tests/test_requirement_intelligence.py -q
`
15 passed, 302 warnings in 14.41s
EXIT:0
`
Test functions (9): test_requirement_intelligence_is_tenant_scoped_and_missing_is_not_found, test_requirement_evidence_requires_write_membership_and_protects_verified_content, test_requirement_assessment_preserves_unknown_and_stale_freshness, test_requirement_paths_require_authentication (parametrized), test_evidence_required_fields_reject_explicit_null (parametrized), test_evidence_wrong_same_org_parent_is_hidden, test_inactive_membership_and_global_admin_policy, test_timezone_rejected_freshness_and_review_gate, test_requirement_search_status_and_unlinked_provenance.

**Coverage inspected (without modifying):**
- Tenant isolation: cross-org 404 (requirement B hidden from A), missing 404 - COVERED
- Viewer denial: VIEWER role blocked on POST/PATCH - COVERED (write_membership test + inactive test)
- Verified-evidence protection: direct VERIFIED on create ->409, UNVERIFIED->VERIFIED without REVIEWED ->409, VERIFIED immutability ->409 - COVERED
- Freshness: UNKNOWN when no date, STALE >90d (2020-01-01), STALE reason string - COVERED
- Invalid parent IDs: wrong same-org parent evidence hidden (404) - COVERED
- Transaction/race: not explicitly tested with concurrent PG transactions; SQLite in-memory fixture - NOT COVERED by this suite (see blockers)
- Additional: timezone normalization (+05:30 -> 06:30 UTC), future-date guard via schema, search(status/query) + unlinked provenance (market_signal_ids == [] when no conversion), INACTIVE membership 403 + global admin 200, null-field 422, unauthenticated 401.

## 5. Frontend typecheck and build

**Typecheck:**
pm.cmd run typecheck (tsc -b --pretty false)
`
EXIT:0
`

**Build:**
pm.cmd run build (tsc -b && vite build)
`
vite v7.3.6 building client environment for production...
transforming ... 59 modules transformed.
dist/index.html 0.70 kB | gzip 0.41 kB
dist/assets/bwip-logo-slCDvDbA.png 1392.99 kB
dist/assets/index-CJaYw3oe.css 23.20 kB | gzip 5.06 kB
dist/assets/index-Dypw3AxN.js 298.86 kB | gzip 88.01 kB
built in 4.52s
EXIT:0
`

**Frontend jsdom tests:**
pm.cmd test (vitest run --environment jsdom)
`
Test Files 8 passed (8)
Tests 20 passed (20)
Duration 51.57s
EXIT:0
`
Includes RequirementEvidenceControls.test.tsx (2): creates classified evidence as UNVERIFIED + viewer hides controls; plus F5CompaniesPage stale-guard, LiveCommandCenter org-scoped dashboard, SourceLink, etc. vmThreads pool warning is performance hint only.

## 6. Database and migration checks actually performed

- **Config isolation:** .env exists, APP_ENV=development, DEBUG=True, DATABASE_URL=postgresql://postgres:postgres123@localhost:5432/bwip_db (local dev only). Without SECRET_KEY, Settings() fails ValidationError: SECRET_KEY must contain at least 32 characters (fails-closed - correct). With synthetic SECRET_KEY=bwip-tests-only-signing-key-never-deploy-2026, settings load OK. This proves production guard works.
- **Test DB isolation:** tests/conftest.py sets synthetic SECRET_KEY + rate limits but does NOT override DATABASE_URL; tests/test_requirement_intelligence.py creates engine sqlite:///:memory: with StaticPool (count 1). No shared/unknown DB was touched. Rule 5 satisfied - no integration/migration run against postgres.
- **Migration inspection:** alembic/versions/t5e6f7a8b9c0_add_requirement_intelligence.py read; creates 3 ENUMs + 2 tables; no alembic upgrade head/current/downgrade was executed (per Rules 4 and 5). No schema was changed.
- **Pre-existing migrations preserved:** s4 F5, u6 pilot JSONB, v7 intelligence JSONB, w8 session/rate limits, x9 google - none executed.

## 7. Browser QA

**Status: BLOCKED - not executed in this bounded gate.**

- **Availability:** @playwright/test 1.64.0 installed, frontend/playwright.config.ts exists (testDir ./browser, workers 1, timeout 45000, baseURL http://127.0.0.1:15173, channel msedge, headless, 3 viewports desktop/tablet/mobile). Capability present.
- **Why not run:** Task requires testing login/org selection/list/detail/evidence workflow/error handling/org switching via live browser. That requires two running instances (frontend Vite + backend uvicorn) on synthetic ports and a disposable DB, plus seeding (scripts/verify_followup_runtime). Per Rules 5 and 8, we do not run integration/browser tests against an unverified shared DB, and do not claim PASS without execution. Prior audit evidence (docs/development/BWIP_COMPLETE_PROJECT_AUDIT.md Final owner-acceptance) records 8 browser scenarios passed at QA evidence port 15173, but this gate does not re-execute or re-claim them.
- **Evidence inspected instead:** RequirementIntelligencePage.tsx stale-guard (active flag, clearTimeout, setRequirements([]) on org switch), debounced search, errorTitle mapping; prior browser evidence retained in referenced audit.

## 8. Confirmed defects

**None found in F6 within this bounded gate.** No code was changed to make tests pass. All 15 F6 tests, typecheck, build, and 20 jsdom tests passed.

*Latent risks noted but not defects:* requirement_confidence always None by design (dimension provenance not recorded - intentional, not a bug); evidence_strength 0 when no evidence; no concurrent-transaction test in this suite (SQLite fixture cannot prove PG row-level races - see blockers).

## 9. Outstanding release blockers

1. **Browser QA not re-executed** - live login/org-switch/evidence workflow at approved viewports remains BLOCKED for this gate; prior pass exists only in referenced audit evidence.
2. **PostgreSQL concurrency not re-proved** - no PG transaction race test (e.g., concurrent evidence creation/verification) executed; SQLite tests pass but cannot prove PG isolation.
3. **Deployed migration not verified** - t5 migration inspected but not run against disposable PG; forward head w8 not re-verified in this gate.
4. **Hosted CI / deployed controls not executed** - no remote CI run, no TLS/HSTS/CSP/ingress/proxy allowlist/production backup-service evidence (inherited from master audit, not F6-specific).

## 10. Final verdict

**BLOCKED**

F6 is **code-complete and locally verified** (15/15 tests, typecheck, build, 20 jsdom, tenant isolation + verified-protection + freshness + invalid-parent + inactive-membership all covered) but **cannot be declared CLOSED** until browser QA and PG-backed checks are re-executed in an isolated disposable environment per the runbook.

## 11. One precise next action

Run the authorized isolated rehearsal without touching production:
`powershell
# In a disposable environment with disposable PG and synthetic key only:

import pathlib
content = open('scripts/tmp_report_body.txt','r',encoding='utf-8').read() if pathlib.Path('scripts/tmp_report_body.txt').exists() else ''
print(len(content))
env:SECRET_KEY='bwip-tests-only-signing-key-never-deploy-2026'; .venv\Scripts\python.exe -m scripts.verify_f6_migrations > .qa-f6-migrations.log 2>&1

import pathlib
content = open('scripts/tmp_report_body.txt','r',encoding='utf-8').read() if pathlib.Path('scripts/tmp_report_body.txt').exists() else ''
print(len(content))
env:SECRET_KEY='bwip-tests-only-signing-key-never-deploy-2026'; .venv\Scripts\python.exe -m scripts.verify_followup_runtime --security-only > .qa-f6-security.log 2>&1
# Then launch browser gate (requires both instances):

import pathlib
content = open('scripts/tmp_report_body.txt','r',encoding='utf-8').read() if pathlib.Path('scripts/tmp_report_body.txt').exists() else ''
print(len(content))
env:SECRET_KEY='bwip-tests-only-signing-key-never-deploy-2026'; .venv\Scripts\python.exe -m scripts.verify_followup_runtime > .qa-f6-runtime.log 2>&1
`
Verify: alembic head w8, row counts, evidence workflow (UNVERIFIED->REVIEWED->VERIFIED 409-gate), org-switch stale discard, and 8/8 browser scenarios PASS before declaring CLOSED. Do not run against the shared bwip_db until disposable target is used.

---
*Generated: 2026-10-11T21:55 Asia/Calcutta | Branch feature/company-module @ a32bf6b | Report: docs/audits/BWIP_F6_RELEASE_GATE_2026-10-11_gate.md*
