# BWIP F6 Isolated Rehearsal and Browser QA — 2026-10-11

**Scope:** F6 Requirement Intelligence isolated verification only. Bounded, non-destructive. No F7, no OAuth mutation, no shared-DB writes, no git reset/clean/commit/push.

## 1. Initial Git state (preserved)

- **Working dir:** E:\BHOODEVI-Warehouse-Intelligence-Platform
- **Branch:** feature/company-module
- **HEAD:** a32bf6b03a174c4a046df75538ddca8c75bbe5f0
- **Log -5:** a32bf6b docs: freeze backend API contract baseline | 1942267 fix: install test client dependency in CI | 15fb034 fix: install pytest in CI | ca035a5 fix: correct prospect prioritization f-string syntax | 50a8cce feat: complete warehouse intelligence backend foundation
- **git status --short:** 39 Modified (see prior gate) + 22 Untracked (includes t5e6f7a8b9c0_add_requirement_intelligence.py, app/api/v1/endpoints/requirement_intelligence.py, app/services/requirement_intelligence.py, app/models/requirement_intelligence.py, alembic s4/u6/v7/w8/x9, frontend browser suites, tests/test_requirement_intelligence.py) — **all preserved, no reset/clean/commit/push**
- **Preservation verified after every phase via subprocess + SECRET_KEY synthetic path**

## 2. Scripts inspected (Phase 1)

### scripts/verify_f6_migrations.py
- **Path verified:** E:\BHOODEVI-Warehouse-Intelligence-Platform\scripts\verify_f6_migrations.py (114 lines)
- **DB target:** Reads settings.DATABASE_URL then derives admin URL via make_url(...).set(database=postgres), requires postgresql backend or RuntimeError. Generates disposable name bwip_f6_audit_ + uuid hex 12, asserts name != original and prefix. CREATE DATABASE <disposable> via admin AUTOCOMMIT, then overrides settings.DATABASE_URL to disposable URL only. Never references bwip_db directly after that.
- **Isolation:** Name uniqueness, prefix check, single-head assertion, F6 doc lookup, pre-F6 down_revision string assertion, cleanup DROP DATABASE <name> WITH (FORCE) + assertion count==0, engine/admin dispose, restores original DATABASE_URL in finally. No code path touches bwip_db except admin catalog queries.
- **Operations:** upgrade head (fresh), downgrade to pre-F6 (s4e5f6a7b8c9), captures schema via inspector (tables != alembic_version, columns types, indexes), inserts org/company/lead/requirement + f5_company_profiles JSON unicode aliases, counts rows per table, upgrades head again, exercises RequirementIntelligenceService.create_evidence / list_requirements / assessment / market_signal_ids, downgrade again asserts schema == before_schema and row counts == before_counts and unicode aliases preserved, re-upgrade head + check.
- **Destructive scope:** Drops only disposable DB, checks absent.
- **Head note:** Script prints Single head + F6 + Pre-F6 but does NOT hardcode w8 — discovers F6 by doc string Add requirement-specific evidence and explainable assessment. Actual graph head discovered x9c0d1e2f3a4 (see 4).

### scripts/verify_followup_runtime.py
- **Path verified:** E:\BHOODEVI-Warehouse-Intelligence-Platform\scripts\verify_followup_runtime.py (235 lines)
- **DB target:** Uses scripts.qa_environment.disposable_database (bwip_followup_ + 12hex, same isolation pattern, migrate=True upgrades to head, DROP WITH FORCE, assert absent). Never uses bwip_db.
- **Services:** free_port(), start_api() spawns uvicorn app.main:app --host 127.0.0.1 --port <free> --no-proxy-headers with env DATABASE_URL=qa_url, AUTH_RATE_LIMIT, EXPENSIVE_RATE_LIMIT, CORS_ORIGINS, DEBUG false; waits /ready 25s; stop() terminates. Two concurrent ASGI instances.
- **Behavior under flags:** --backup-only seeds then backup_restore only; --security-only runs sessions + distributed rate limits then returns PASS; full runs sessions, distributed, then Vite on 15173 + npm run test:browser, then backup_restore, asserts browser returncode==0 else AssertionError but still cleans disposable DBs.
- **Coverage:** sessions (logout across instances, restart isolation, password change, admin revoke/deactivation, membership removal), distributed quotas (shared 429 across instances, spoofed headers, Retry-After, expiry, 503 fail-closed), browser (qa.e2e.ts + company.e2e.ts across 3 viewports), backup_restore (pg_dump custom + pg_restore, row counts, alembic check, tenant ownership, restored app writes), concurrency (via postgres-concurrency.json — row locks, idempotent retry, duplicate unique constraint, rollback).
- **Cleanup:** Restores settings.DATABASE_URL, disposes engine/admin, drops disposable DBs (both bwip_followup_ and bwip_f6_audit variants), stops processes.

### scripts/qa_environment.py
- Verified: disposable_database contextmanager, seed() creates synthetic users member/viewer/admin/other, orgs A/B, memberships, companies, F5 profiles, leads, requirements, warehouses, stages, matches, signals, candidates — all synthetic Synthetic QA / example.com scope.

## 3. Alembic graph truth

- Config: alembic.ini script_location %(here)s/alembic, sqlalchemy.url via app.core.config settings.DATABASE_URL
- Heads: Single head x9c0d1e2f3a4 ( Optional Google identity linking and single-use sign-in challenges. )
- Walk: x9c0d1e2f3a4 -> w8b9c0d1e2f3 -> v7a8b9c0d1e2 -> u6f7a8b9c0d1 -> t5e6f7a8b9c0 (F6: Add requirement-specific evidence and explainable assessment.) -> s4e5f6a7b8c9 -> r3d4e5f6a7b8 -> q2c3d4e5f6a7 -> p1b2c3d4e5f6 -> ... -> cdef4c027ca2 -> None (32 revisions total, linear, no branch)
- Downgrade target for F6 rehearsal: s4e5f6a7b8c9 (pre-F6) — correct.
- Prior note mentioning w8 as head is stale; actual head is x9. bwip_db currently at w8b9c0d1e2f3 (behind by one x9 migration) — intentional dev state, not a rehearsal failure. Rehearsal ran against disposable DB at head x9.


## 4. Commands executed and exit codes

| # | Command | Exit | Notes |
|---|---|---|---|
| 1 | git rev-parse HEAD | 0 | a32bf6b03a174c4a046df75538ddca8c75bbe5f0 |
| 2 | git branch --show-current | 0 | feature/company-module |
| 3 | git log --oneline -5 | 0 | a32bf6b, 1942267, 15fb034, ca035a5, 50a8cce |
| 4 | git status --short | 0 | preserved |
| 5 | $env:SECRET_KEY=...; python -m scripts.verify_f6_migrations > .qa-f6-migrations.log 2>&1 | 0 | disposable bwip_f6_audit_fcf46b9178c5, head x9 verified |
| 6 | python -m scripts.verify_followup_runtime --security-only | 0 | bwip_followup_96d572245659, sessions+quotas PASS |
| 7 | python -m scripts.verify_followup_runtime (full) | 1 | browser assertion failed — company suite 5 failures; qa suite PASS; disposables dropped |
| 8 | admin PG probe (synthetic SECRET_KEY) | 0 | make_url(....set(database='postgres')) OK, bwip_db w8 |

Prior checks NOT rerun: pytest 15 passed, typecheck 0, build 0, frontend tests 20 passed.

## 5. PostgreSQL isolation evidence

- **Configured DATABASE_URL:** postgresql://postgres:***@localhost:5432/bwip_db (local only, redacted).
- **Admin catalog:** SELECT datname FROM pg_database ordered — shows bwip_db, parity/validation leftovers, postgres, templates. After rehearsals SELECT LIKE 'bwip_f6_audit_%' returned 0 rows; LIKE 'bwip_followup_%' retained only pre-existing leftovers from prior runs unrelated to this gate — both F6 disposables verified absent (fcf46b9178c5, 96d572245659, 4853b13a4b55, 1977b39c0350 all dropped).
- **Disposable proof:** log "Disposable database: bwip_f6_audit_fcf46b9178c5" + "Single head: x9c0d1e2f3a4 F6: t5e6f7a8b9c0 Pre-F6: s4e5f6a7b8c9"; cleanup "PASS cleanup: exact disposable database and dependent QA rows removed" + assertion count==0; final admin check count==0.
- **bwip_db untouched:** No CREATE/DROP touching bwip_db; post-rehearsal SELECT version_num = w8b9c0d1e2f3 (unchanged), public tables 46, no downgrade run against bwip_db. Rehearsal only on disposable (head x9 not applied to bwip_db).
- **Credentials:** Never printed; logs only "postgresql://postgres:***". DATABASE_URL restored in finally.

## 6. Migration rehearsal results (Phase 2)

- Script: scripts/verify_f6_migrations.py EXIT 0, log .qa-f6-migrations.log 34410 bytes
- Head verified: Single head x9c0d1e2f3a4 (correct; w8 note stale — x9 adds google_subject). F6 t5e6f7a8b9c0 doc "Add requirement-specific evidence..." located, pre-F6 s4e5f6a7b8c9.
- Upgrade/downgrade/re-upgrade:
  - PASS fresh base-to-head: 32 upgrades cdef4c027ca2..x9, "x9c0d1e2f3a4 (head) No new upgrade operations detected."
  - Downgrade to s4e5f6a7b8c9, snapshot inspector (exclude alembic_version), seed synthetic org/company/lead/requirement + f5_company_profiles unicode ['synthetic','unicode-仓库'], count rows.
  - PASS pre-F6-to-head: create_evidence UNKNOWN now, list_requirements query, assessment.freshness FRESH, market_signal_ids [], aliases preserved.
  - Downgrade: schema()==before_schema, row counts==before_counts, unicode preserved.
  - PASS re-upgrade + check no drift.
- F6 objects: 3 ENUMs + 2 tables requirement_intelligence_evidence (ix_*__requirement/__organization, FK cascade, default UNVERIFIED) and requirement_intelligence_assessments (unique requirement_id, 7 Numeric(5,2), JSON reasons, default UNKNOWN) — present after upgrade, absent after downgrade, present after re-upgrade.
- Cleanup: DROP DATABASE bwip_f6_audit_fcf46b9178c5 WITH (FORCE), assertion absent.
- **Verdict PASS** — migration blockers cleared.

## 7. Runtime and concurrency (Phase 3)

### 7a. Security-only (EXIT 0)
- Disposable bwip_followup_96d572245659, 32 upgrades, log .qa-f6-security.log 5148 bytes.
- sessions.json PASS (2 instances): logout+restart, password change, admin revoke/deactivation, membership removal.
- distributed-rate-limits.json PASS: auth 200:6 429:4, expensive 200:3 429:5 — shared quota across 2 uvicorns, spoofed headers no bypass (--no-proxy-headers), Retry-After, expiry, 503 fail-closed.

### 7b. Full runtime + browser + backup (EXIT 1 — browser-driven)
- Disposables bwip_followup_4853b13a4b55/1977b39c0350 (nested), log .qa-f6-runtime.log ~34KB.
- sessions + distributed PASS before browser.
- Backup-restore PASS: backup-restore.json status PASS local synthetic restore, revision x9c0d1e2f3a4, tables 47, sha256 3d4556f..., recovery 12.88s, pg_dump + pg_restore, row counts match, no drift, tenant preserved, restored app health/login/foreign denial + new match. Archive deleted.
- Concurrency PASS (postgres-concurrency.json): 7 checks — candidate conversion row-lock retry, warehouse conversion retry, generation one match, conflicting transitions serialized, duplicate deal constraint, downstream failure rollback+retry, verification vs edit provenance.

## 8. Browser QA (Phase 4)

- Config: frontend/playwright.config.ts — ./browser **/*.e2e.ts workers 1 timeout 45000 baseURL 127.0.0.1:15173 channel msedge headless chromiumSandbox screenshot only-on-failure projects desktop/tablet/mobile.
- Suites: qa.e2e.ts (8 specs: login/storage, F5/market switching, viewer read-only, requirement evidence conversions, direct nav, human signal/candidate) + company.e2e.ts — all against disposable synthetic backend.
- Execution: verify_followup_runtime full — 2 uvicorn + Vite 15173 then npm run test:browser. Duration 137331ms stats expected 12 skipped 22 unexpected 5 flaky 0. Prior before-repairs: expected 4 unexpected 3.

| # | Workflow | Desktop | Tablet | Mobile |
|---|---|---|---|---|
| 1 | Login and authenticated session | PASS (7836+4180ms) | skipped | skipped |
| 2 | Requirement Intelligence nav | PASS | PASS | PASS |
| 3 | Requirement list/search/status | BLOCKED — company search suite failed; no requirement search browser spec in qa.e2e.ts (unit-only) | — | — |
| 4 | Requirement detail/assessment | PASS (6816ms) | skipped | skipped |
| 5 | Evidence display/edits | PASS (Add -> Mark reviewed -> Reject) | skipped | skipped |
| 6 | Verified-evidence protection | PASS (REJECTED removes Mark reviewed + 409 unit gates) | — | — |
| 7 | Org switching + stale | PASS (F5 4085 + market 3607 + company stale 5623) | skipped | skipped |
| 8 | Unauthorized + recoverable | PASS (viewer 4131 + direct nav 4210) | PASS | PASS |

- Failures (5, all company.e2e.ts, NOT qa.e2e.ts): desktop list/detail synthetic.contact@example.com not found; desktop empty dataset Sign out not visible; desktop network optional profile text not found; tablet/mobile list/detail same synthetic.contact@example.com.
- F6 qa.e2e.ts 8/8 expected PASS on desktop (workflows 1,2,4,5,6,7,8). Workflow 3 has no browser spec — unit-only.


## 9. Regression and defects

- No F6 defects. No schema/migration history changed.
- 824 backend suite retained from prior acceptance; not rerun.
- Company-detail contact rendering defect noted out-of-scope for F6.

## 10. Files changed / created

- Created: docs/audits/BWIP_F6_ISOLATED_REHEARSAL_2026-10-11.md (this report), .qa-f6-migrations.log, .qa-f6-security.log, .qa-f6-runtime.log, browser-results.json overwritten (91302), sessions/distributed/backup-restore/postgres-concurrency.json updated. tmp helpers scripts/tmp_*.txt/.py (removable, not F6).
- Not modified: bwip_db w8b9c0d1e2f3, no git reset/clean/commit/push, no migration edits, prior audits preserved.

## 11. Final F6 verdict

**NOT CLOSED — isolated PASS for migration/runtime, browser PASS for 7/8 F6 workflows, BLOCKED on workflow 3 browser search.**

- Migration: PASS (isolated upgrade/downgrade/re-upgrade, head x9, F6 ENUMs/tables proven, bwip_db untouched).
- Runtime + concurrency: PASS.
- Browser: PASS 7/8; workflow 3 (list/search/status) has no browser execution — unit-only.
- Smallest next step: Add minimal qa.e2e.ts test for Requirement Intelligence list/search/status (search "Synthetic Demand" -> filter ACTIVE -> assert list, org-switch clears stale), then run full verify_followup_runtime in isolated disposable env. No F6 backend change expected unless test exposes bug. Company suite failures triaged separately.

## 12. Next command (isolated only)

```
$env:SECRET_KEY='bwip-tests-only-signing-key-never-deploy-2026'; .venv\Scripts\python.exe -m scripts.verify_followup_runtime
```

Do not run against bwip_db. Declare CLOSED only when workflow 3 browser search passes.

---
*Generated: 2026-10-11 | feature/company-module @ a32bf6b | Report: docs/audits/BWIP_F6_ISOLATED_REHEARSAL_2026-10-11.md | Logs: .qa-f6-migrations.log, .qa-f6-security.log, .qa-f6-runtime.log | Evidence: docs/development/evidence/2026-10-10/{browser-results,backup-restore,sessions,distributed-rate-limits,postgres-concurrency}.json*
