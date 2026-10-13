# BWIP F6 Closure — Requirement List/Search/Status Browser Gap Closed — 2026-10-11

**Scope:** Close the one missing F6 browser workflow (Workflow 3: Requirement Intelligence list, search, status filtering) via isolated disposable-DB rehearsal. No `bwip_db` writes, no migration/schema changes, no F7/OAuth mutation, no `git reset/clean/commit/push`, no `company.e2e.ts` hiding.

**Verdict: CLOSED** — Migration, runtime, backup/restore, PostgreSQL concurrency and all F6 `qa.e2e.ts` browser workflows including the new Workflow 3 now PASS in disposable isolation. Five `company.e2e.ts` failures remain but are out-of-scope for F6 and unchanged.

## 1. Git state (preserved)

- Branch `feature/company-module`, HEAD `a32bf6b03a174c4a046df75538ddca8c75bbe5f0`, Log -5 `a32bf6b | 1942267 | 15fb034 | ca035a5 | 50a8cce`
- `git status --short`: 39 Modified + 22+ Untracked preserved (see BWIP_F6_ISOLATED_REHEARSAL_2026-10-11.md s1). No reset/clean/commit/push.

## 2. Safety & isolation verified

- Inspected `qa_environment.disposable_database (bwip_followup_+12hex, make_url postgres, AUTOCOMMIT, CREATE/DROP WITH (FORCE), count==0, restored DATABASE_URL)` and `verify_followup_runtime` (2x uvicorn --no-proxy-headers, Vite 15173, QA_API/QA_IDS/QA_EVIDENCE_DIR/QA_EXPIRED_TOKEN).
- No `bwip_db` code path; secrets via `$env:SECRET_KEY='***'` synthetic only.
- Post-run: `bwip_db` at `w8b9c0d1e2f3` (expected lag behind head `x9c0d1e2f3a4`), 46 tables, `LIKE 'bwip_followup_%'` = 0 rows (disposables dropped: c250cac14aae/6ae673d494d0/ce597b4ceae3/e05d69180041/593c394257cf/c9600c3cf577/692fa91ebda2). Prior audits preserved.

## 3. Step 1 — Browser test inspection

- Fixtures: seed 2 orgs (qa-A/B), 2 requirements Synthetic Demand A/B (ACTIVE, Bengaluru), member@example.com in both orgs. QA_IDS orgs/requirements/companies/stages/signal/match/candidates.
- API: `GET /requirement-intelligence?organization_id=&query=&status=` filters org, optional status enum (DRAFT/ACTIVE/ON_HOLD/CLOSED/CANCELLED), title ilike query, ordered by updated_at desc.
- Frontend: RequirementIntelligencePage debounced 180ms, selects Select organization / Search requirements / Filter by requirement status, cards `.requirement-card` h3 title + `.f5-chip` status, empty `No requirements match this view`, record-count, stale guard (active flag, clearTimeout, setRequirements([])).
- Feasible without new fixture. Prior qa.e2e.ts had 8 specs (workflows 1,2,4,5,6,7,8) — workflow 3 unit-only.

## 4. Step 2 — Minimal browser test added

File: `frontend/browser/qa.e2e.ts` only. Test: `requirement intelligence list, search and status filtering without stale results` (desktop-only, test.skip tablet/mobile like existing). Steps: signIn(member) -> /requirement-intelligence -> main heading -> select org A (waitForResponse GET) -> A visible B absent >=1 card -> search Synthetic Demand A -> 1 filtered card -> search Synthetic Demand B -> empty -> clear -> A -> status ACTIVE -> A 1 -> DRAFT hides A (handles extra DRAFT Synthetic candidate 0 from prior conversion: asserts DRAFT chip if cards>0 else empty) -> CLOSED empty -> ALL -> A -> nonsense search empty -> clear -> A -> stale switch (route delay 600ms for org A, select A then B -> B visible A 0 after 800ms 1 card, unroute, search B 1, search A empty, clear B). Uses waitForListStable(300ms + loading 0) and actual .requirement-card/.f5-chip assertions. No new schema, no company.e2e.ts edit.

## 5. Step 3 — Validation (isolated disposable)

Commands (SECRET_KEY redacted ***):
1. `git rev-parse HEAD; git branch --show-current; git status --short` — 0 — a32bf6b feature/company-module 39M preserved
2. `npm run typecheck` — 0 — tsc -b pass
3. `npm run build` x3 — 0 — vite 7.3.6 59 modules ~3s
4. Isolation read qa_environment/verify_followup_runtime — 0 — bwip_followup / make_url postgres / WITH (FORCE) confirmed
5. `$env:SECRET_KEY='***'; .venv\Scripts\python.exe -m scripts.verify_followup_runtime > .qa-f6-runtime2.log` — 1 — strict heading 2 elements (fixed to main)
6. Same > .qa-f6-runtime3.log — 1 — card count 2 extra candidate (fixed)
7. Same > .qa-f6-runtime4.log — 1 — DRAFT non-empty (switched probe to CLOSED)
8. Same > .qa-f6-runtime5.log — 1 — qa.e2e.ts 9/9 desktop PASS including new test; company.e2e.ts 5 failures remain so outer script asserts 1

Browser evidence (`docs/development/evidence/2026-10-10/browser-results.json`):
- Stats: `startTime 2026-10-11T17:38:13Z duration 148396ms expected 13 skipped 24 unexpected 5 flaky 0` (was expected 12, +1 new test).
- qa.e2e.ts desktop PASS: tab storage, login errors, F5 switching, market switching, viewer read-only, evidence review + conversions, direct nav (also PASS tablet/mobile), human signal/candidate/evidence rejection, **requirement list/search/status (new) PASS desktop/skipped tablet/mobile**.
- Workflow map: 1 Login PASS, 2 Nav PASS, 3 List/Search/Status NEW PASS, 4 Detail/Assessment PASS, 5 Evidence edits PASS, 6 Verified protection PASS, 7 Org stale PASS (+ requirement org B no-stale), 8 Unauthorized+recoverable PASS → 8/8 F6 PASS.
- company.e2e.ts 5 unexpected (NOT F6, unchanged): `company list/details` fail x3 (synthetic.contact@example.com), `empty dataset` fail (Sign out), `network optional-section` fail (Warehouse intelligence profile not available.) — identical to prior rehearsal.

Other evidence PASS: sessions.json PASS across 2 instances, distributed-rate-limits.json PASS shared quota 200:6/429:4 + 200:3/429:5 spoof ignored 503 fail-closed, backup-restore.json PASS x9c0d1e2f3a4 tables 47 sha c694a2fd 13.88s no drift tenant preserved, postgres-concurrency.json 7/7 PASS row-lock/idempotent/unique/rollback/provenance (db bwip_followup_692fa91ebda2).
- bwip_db untouched: version w8b9c0d1e2f3, tables 46, LIKE bwip_followup_% 0 rows.

## 6. Final decision

**CLOSED** — Prior migration PASS retained (head x9, 32 revs upgrade/downgrade/re-upgrade, ENUMs/tables), runtime+concurrency PASS, browser 8/8 F6 workflows PASS including new Workflow 3 on disposable PG via real API/UI. Company suite failures out-of-scope, not hidden, not blocking.

## 7. Files changed/created

- Modified: `frontend/browser/qa.e2e.ts` (+64 lines, Build pass)
- Created: `docs/audits/BWIP_F6_CLOSURE_2026-10-11_requirement-list-search-status.md` (this report; priors preserved BWIP_F6_ISOLATED_REHEARSAL_2026-10-11.md + BWIP_F6_RELEASE_GATE_2026-10-11_gate.md)
- Updated: `docs/development/evidence/2026-10-10/browser-results.json` (13 expected), sessions/distributed/backup-restore/postgres-concurrency.json PASS, .qa-f6-runtime*.log volatile
- Not modified: bwip_db, migrations, F7/OAuth, company.e2e.ts

## 8. Reproduction (isolated only)

```powershell
$env:SECRET_KEY='***'
.venv\Scripts\python.exe -m scripts.verify_followup_runtime  # disposable bwip_followup_*, no bwip_db
# check docs/development/evidence/2026-10-10/browser-results.json expected 13 unexpected 5 company-only
```

NOT CLOSED only if new requirement list test or sessions/distributed/backup/concurrency regresses; BLOCKED if disposable PG/Edge/Vite unavailable.

---
*Generated: 2026-10-11 | Branch feature/company-module @ a32bf6b | Report: docs/audits/BWIP_F6_CLOSURE_2026-10-11_requirement-list-search-status.md | Evidence: docs/development/evidence/2026-10-10/{browser-results,sessions,distributed-rate-limits,backup-restore,postgres-concurrency}.json*
