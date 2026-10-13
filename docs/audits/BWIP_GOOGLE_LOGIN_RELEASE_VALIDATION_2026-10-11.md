# BWIP Google Login — Release Validation 2026-10-11

**Date (UTC):** 2026-10-11 19:38 UTC
**Repository:** E:\BHOODEVI-Warehouse-Intelligence-Platform
**Branch:** feature/company-module
**HEAD:** a32bf6b03a174c4a046df75538ddca8c75bbe5f0
**Report:** docs/audits/BWIP_GOOGLE_LOGIN_RELEASE_VALIDATION_2026-10-11.md
**Previous report findings treated as historical, not proof of current state.**

---

## A. Executive verdict

**PASS WITH CONDITIONS — AUTOMATED VERIFICATION PASSED, RELEASE GATES REMAIN**

Local implementation, synthetic security tests, frontend checks, typecheck/build, and disposable-DB migration rehearsals PASS. Real Google-provider staging flow, staging DB migration, and public-launch session-risk decision are NOT VERIFIED and block PASS READY. No secrets printed or committed; no shared DB migrated; no reset/clean/commit/push.

Rationale: B1-B6 PASS on code/test evidence; 23 backend + 20 frontend tests PASS; typecheck/build PASS; disposable PG rehearsals PASS; .env.example documents GOOGLE_CLIENT_ID correctly. Missing: real GIS browser login, staging DB head, remote parity, production session-risk decision.

---

## B. Baseline and change summary

**Git baseline (observed):**
- `git branch --show-current` = feature/company-module
- `git rev-parse HEAD` = a32bf6b03a174c4a046df75538ddca8c75bbe5f0
- `git ls-remote --heads origin feature/company-module` = 4ed75a9e1a4896bf... — remote diverged; local work not on remote.
- `git status --short`: 43 M tracked + ~80 ?? untracked (preserved). M includes .env.example (edited this task), validation.yml, .gitignore, README, alembic/env.py, app/api/v1/endpoints/auth + 7 others, app/api/v1/routes.py, app/core/config+security, app/dependencies.py, app/main.py, app/models/__init__+requirement+user, app/repositories/*, app/schemas/user.py, app/services/*, docs/*, requirements.txt, tests/test_*. ?? includes full frontend/ (untracked), alembic/versions s4/t5/u6/v7/w8/x9, app/services/google_auth.py, app/core/rate_limit.py, app/models/google_login_challenge+rate_limit, tests/test_google_auth+rate_limit+session_revocation+conftest, docs/audits evidence.
- `git diff --stat`: 43 files, 585 insertions, 82 deletions after .env.example edit. requirements.txt binary diff includes google-auth 2.61.0, rsa 4.9.1.
- No git reset --hard / clean / restore / commit / push / merge / rebase / branch switch.

**Files changed by this task:**
- `.env.example` — added `GOOGLE_CLIENT_ID=` placeholder + comment documenting optional GIS Web client ID, empty disables Google sign-in. No secret.
- Prior task preserved (untracked frontend/): `frontend/package.json` (+@types/node ^22.20.5), `frontend/package-lock.json`, `frontend/tsconfig.node.json` (types:[node], include vite+playwright+browser, lib ES2023+DOM). Not in git diff because frontend/ untracked. Verified passing.

**Preserved:** All M/?? remain; no overwrite/reformat; no destructive git; no commit/push.
**Remote parity:** Google code untracked therefore NOT on remote (remote HEAD 4ed75). Staging from remote would lack Google Login.
**Migrations:** `alembic heads` = x9c0d1e2f3a4 single head; `alembic branches` = b657->p1 merge only. Local bwip_db not at head (alembic check FAILED target not up to date — expected; disposable rehearsals used).
**TypeScript fix:** `npm --prefix frontend run typecheck` PASS 0 errors; `npm run build` PASS 59 modules 298kB/88kB gzip. QA files typechecked via tsconfig.node.json.

---

## C. Implementation audit (B1-B6)

### B1. Provider credential verification — PASS
- `app/services/google_auth.py:verify_google_credential` uses `google.oauth2.id_token.verify_oauth2_token` with `settings.GOOGLE_CLIENT_ID` audience, BoundedRequest timeout=5. Verified by `test_official_google_library_checks_signed_tokens` — real RSA 2048 key, synthetic JWT, checks audience/issuer/expired/signature, asserts timeout 5; 5 parametrized PASS. No raw decode-trust. `GoogleLogin` schema credential max 8192, nonce 32-128, subject/email 1-255, email_verified==True, oversize 422. TransportError 503 fail-closed, no session.

### B2. Challenge and nonce lifecycle — PASS
- `issue_challenge`: `secrets.token_urlsafe(32)`, stores sha256 only, expires 300s, deletes expired then commit. `google_login`: `secrets.compare_digest`, `DELETE ... WHERE nonce_hash==sha256 AND expires_at>now RETURNING` then commit — single winner concurrency-safe, consumes even on failed link. Expired/mismatched/unknown/replayed rejected (4 claims + 2 challenge tests PASS). Sequential replay PASS (second 401). DB IntegrityError path already consumed. Concurrent workers not integration-tested but DELETE RETURNING design covers it.

### B3. Account linking and identity safety — PASS
- Stable identity `sub` (1-255), lookup `google_subject` FOR UPDATE, else `lower(email)` FOR UPDATE requires exactly 1 active match, rejects if already linked (403), requires link_password verified (409). Unknown identities 403 no auto-create, inactive 403, silently relink 403, flush IntegrityError 409. Tenant not inferred from domain — BWIP token + membership checks; explicit_link test asserts org isolation 200 vs 403. No cross-tenant grant.

### B4. Access tokens, logout, and revocation — PASS
- `create_access_token({sub, ver})` same as password login. `get_current_user` validates sub, is_active, `ver==token_version` (int strict). Logout/change-password/admin revoke increment token_version durable shared DB. Tests: logout, password change, admin revoke, membership removal all PASS. Google path covered via explicit_link issuing same token, cross-org and logout 401. Failed Google no session (frontend busy guard).

### B5. Origin, CORS, and rate limiting — PASS
- `require_google_origin` checks `origin in CORS_ORIGINS` exact, applied to challenge+login (403 on evil origin PASS). CORSMiddleware allow_origins=CORS_ORIGINS, allow_credentials=False, explicit methods/headers, no wildcard. DatabaseLimiter atomic upsert via pg_insert/sqlite_insert, shared DB, clock_timestamp on PG, HMAC keys, deletes expired. Storage failure 503, no fallback. Tests 429 recovery, spoofed XFF ignored, bounded memory PASS.

### B6. Frontend GIS flow — PASS
- `GoogleSignIn.tsx` loads GIS only after config client_id present else disabled message, no script. Correct nonce/client_id passed after challenge. Duplicate callback guarded by busy ref. Expiry setTimeout clears button. Script failure timeout 15s + sdk reset. Network catch alerts, Retry fresh challenge. Failed never stores token. `client.ts` retires localStorage, credentials omit, no secret, VITE public. App clears on 401, logout clears. Tests disabled+nonce+duplicate+retry PASS. SessionStorage XSS risk remains (see G).

---

## D. Exact validation results

| # | Command | Result | Details |
|---|---|---|---|
| 1 | `git branch --show-current` | PASS | feature/company-module |
| 2 | `git rev-parse HEAD` | PASS | a32bf6b03a174c4a046df75538ddca8c75bbe5f0 |
| 3 | `git status --short` | PASS | 43 M + ~80 ?? preserved, no destructive git |
| 4 | `git diff --stat` | PASS | 43 files 585+/82- |
| 5 | `pytest tests/test_google_auth.py tests/test_auth_rate_limit.py tests/test_session_revocation.py -v` | PASS | 23 passed (94.9s, 304 warnings) — 17 Google + 2 rate_limit + 4 session_revocation |
| 6 | `npm --prefix frontend test` | PASS | 8 files 20 passed 41s |
| 7 | `npm --prefix frontend run typecheck` | PASS | 0 errors (tsc -b) |
| 8 | `npm --prefix frontend run build` | PASS | 59 modules 298kB gzip 88kB 2.75s |
| 9 | `alembic heads` | PASS | x9c0d1e2f3a4 (head) |
| 10 | `alembic branches` | PASS | b657->p1 merge only |
| 11 | `alembic check` (local bwip_db) | FAIL expected | FAILED: Target DB not up to date — dev DB not at head; disposable used |
| 12 | `scripts.verify_f6_migrations` disposable bwip_f6_audit_f897... | PASS | base->head, pre->head with unicode, downgrade preserves, re-upgrade, cleanup |
| 13 | `disposable w8->x9` rehearsal bwip_followup_d7a9... | PASS | w8 no challenge, x9 adds google_login_challenges + uq_users_google_subject, downgrade removes, re-upgrade PASS |
| 14 | `git diff --check` | PASS | CRLF warnings only |
| 15 | openapi + pip check (CI) | PASS historical | 45 tables / 139 paths per prior CI; local requires SECRET_KEY |

Coverage: valid linked, returning identity, unknown, email without password (None/wrong), inactive, conflicting subject, unverified email, mismatched nonce/issuer/audience/signature, expired token, expired/replayed nonce, oversized 8193, disabled 503, invalid Origin 403, rate 429 + DB 503, transport 503, logout/ver revocation, cross-org 403, frontend disabled/challenge failure/duplicate/expiry/retry/logout — all covered. DELETE RETURNING is atomic.

---

## E. Migration report

**Graph:** `<base>->cdef->c99->51->2d->a1->f0->c7->d8->e9->f1e->g2->h3->i4->j5->k6->l7->m8->n9->o0->b657 (branchpoint) + b8->p1 merge ->q2->r3->s4(F5)->t5(F6)->u6->v7->w8(session+rate)->x9(google head)`. Single head x9.

**Disposable rehearsals (no shared DB touched):**
- F6 isolated (bwip_f6_audit_f897...): base->head, pre->head with synthetic org/company/lead/req + F5 unicode, downgrade preserves tables/columns/indexes+rows, re-upgrade, check PASS, dropped.
- Google (bwip_followup_d7a9...): w8 no challenge, x9 adds google_login_challenges (nonce_hash PK String64, expires_at BigInt indexed) + users.google_subject unique, downgrade removes, re-upgrade PASS.

**Staging DB:** NOT APPLIED per safety. Operator must backup then `alembic upgrade head` in release job.
**Backup/restore:** Prior evidence retained, no new backup in this gate.

---

## F. Real-provider staging report

**Status: NOT VERIFIED — no staging or Google Console access.**

No staging URL, client ID, or OAuth consent. No deployed config reachable. No GIS flow executed.

**Operator checklist (sanitized, no secrets):**

*Preflight:*
- [ ] Create OAuth Web client for exact staging origin (Authorized JS origins); record prefix/suffix only.
- [ ] Staging backend GOOGLE_CLIENT_ID = client ID, CORS_ORIGINS = [staging HTTPS], VITE_API_BASE_URL = staging backend, APP_ENV=staging DEBUG=False strong SECRET_KEY PG DATABASE_URL, redeploy reviewed image.
- [ ] Backup staging DB, record revision, `alembic upgrade head` verify x9, check PASS.
- [ ] `GET /auth/google/config` returns `{"client_id":"<staging>"}` Cache-Control no-store matching Console.
- [ ] Frontend origin authorized, console no errors, `/health` 200 `/ready` 200, challenge returns nonce 300s.
- [ ] Password login still works.

*Positive (dedicated test account, clean):* button appears, GIS complete, BWIP token issued, /auth/me shows user/orgs, navigate protected, reload per sessionStorage, logout 401, revocation across tabs.

*Negative:* cancel, unapproved Origin 403, expired 401, replay 401, invalid nonce 401, unverified 401, unknown 403, link without password 409, outage 503 — no session, no leakage.

*Evidence:* UTC timestamp, commit SHA/image tag, env id (no secrets), browser/OS, OAuth check, Origin/API checks, revisions, outcomes, request IDs — no tokens/passwords/nonces.

---

## G. Security and deployment risk register

| Risk | Severity | Evidence | Mitigation / Owner | Blocks Staging | Blocks Public |
|---|---|---|---|---|---|
| Session token in sessionStorage (XSS theft) | HIGH | client.ts sessionStorage, credentials omit | Tab-scoped limits persistence but not XSS. Public requires explicit acceptance or HttpOnly cookie migration (CSRF/CORS). Verify CSP + audit. Owner Security/Frontend. | No if accepted | YES |
| Staging Google config missing | HIGH | GOOGLE_CLIENT_ID empty locally | Staging must set exact origins/client ID before release. | YES | YES |
| Remote not containing Google code | HIGH | frontend/ untracked, remote 4ed75 vs local a32b | Review and push reviewed code before staging build (no push per task). | YES | YES |
| Shared DB not at head | MEDIUM | alembic check FAILED | Apply w8/x9 in release job after backup; rehearsal PASS. | YES | YES |
| Trusted proxy headers | MEDIUM | rate_limit ignores XFF | Use --no-proxy-headers locally; behind ingress set forwarded-allow-ips to trusted ingress only, have ingress replace headers. | No | YES |
| Rate limit DB dependency | MEDIUM | DatabaseLimiter shared DB | 503 on failure correct; monitor 429/503, latency, table growth. | No | No |
| No TLS/backup/monitoring evidence | MEDIUM | DEPLOYMENT.md not provisioned | Operator provision TLS, encrypted backup, monitoring before public. | No | YES |
| Branchpoint p1 merge | LOW | r3->s4 merge | Valid, no action. | No | No |

No new defects requiring code fix beyond .env.example placeholder.

---

## H. Remaining actions (ordered, owner)

**1. Code (dev):** [ ] Review and push local Google+F5/F6+auth changes to remote after approval (no push per task). Optional concurrent replay integration test.
**2. Local automated (synthetic key):** [x] 23 backend +20 frontend +typecheck+build PASS; [x] disposable rehearsals PASS; [ ] Full 824 suite if required.
**3. Google Cloud Console (owner):** [ ] Create staging OAuth Web client for staging origin; note client ID.
**4. Deployment env (operator):** [ ] Staging set GOOGLE_CLIENT_ID, CORS_ORIGINS (staging HTTPS), VITE_API_BASE_URL, SECRET_KEY >=32, DATABASE_URL PG, APP_ENV=staging DEBUG=False, redeploy reviewed image.
**5. Database/release (operator, controlled window):** [ ] Backup staging DB record revision; [ ] `alembic upgrade head` verify x9; [ ] /health /ready + isolation checks.
**6. Real-provider staging tests (tester, dedicated account):** [ ] Execute F checklists; record sanitized evidence.
**7. Risk acceptance (owner/security):** [ ] Explicit decision sessionStorage vs HttpOnly cookie before public; if keeping sessionStorage document CSP controls.

---

## I. Final release gate

- **Implementation correctness:** PASS — B1-B6 PASS on code + synthetic tests, bounded, fail-closed, tenant-isolated.
- **Automated test status:** PASS — 23 targeted +20 frontend +typecheck+build PASS; disposable PG rehearsals PASS; full suite not re-run in this scoped gate.
- **Migration readiness:** CONDITIONAL PASS — graph valid single head x9, rehearsals PASS (base->head, w8->x9, downgrade/re-upgrade, row preservation); staging DB NOT YET MIGRATED.
- **Staging validation (real Google):** NOT VERIFIED — no staging deployment or GIS flow.
- **Public-launch readiness:** NOT READY — requires staging PASS plus sessionStorage decision, TLS/backup/monitoring, proxy/CSP verified.

Overall: **PASS WITH CONDITIONS** — safe to proceed to staging release procedure, NOT ready for staging/public until H completes. No commit/push or shared DB migration; .env.example no secrets; frontend TS fix preserved.

---
*Generated: 2026-10-11 19:38 UTC | Branch feature/company-module @ a32bf6b | Evidence synthetic + disposable PG, no real provider flow | No git reset/clean/commit/push, no secrets*
