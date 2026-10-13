# BWIP Master Repair and Release Validation — 2026-10-12

- **Baseline (remote tip):** `4ed75a9e1a4896bfedadb2d36f09c2e2c4564d41` `docs: record approved F7 architecture decisions` (parent `a32bf6b`, +41 lines F7 D1-D10, preserved as ancestor)
- **Local HEAD at start:** `a32bf6b03a174c4a046df75538ddca8c75bbe5f0` (43 M + 211 ?? `git status`; `diff --cached` empty; behind 1, ahead 0)
- **Candidate:** `E:/BHOODEVI-Warehouse-Intelligence-Platform-candidate` on branch `release/candidate-2026-10-12` tracking `origin/feature/company-module` at `4ed75a9`; original worktree left dirty on `a32bf6b` and untouched
- **Isolation:** `git worktree add -b release/candidate-2026-10-12 E:/...-candidate origin/feature/company-module` — no `reset --hard`/`clean`/`checkout`/`stash` in original worktree; F7 decision record intact
- **No push/merge/publish performed** — candidate remains unpublished until human `git push origin feature/company-module` (FF)

## Scope decision — why F5/F6 cannot be omitted

Verified migration chain: `r3d4e5f6a7b8 -> s4e5f6a7b8c9 -> t5e6f7a8b9c0 -> u6f7a8b9c0d1 -> v7a8b9c0d1e2 -> w8b9c0d1e2f3 -> x9c0d1e2f3a4` where `w8 (session revocation + RateLimitBucket)` and `x9 (google_subject + google_login_challenges)` descend from `s4 (F5)` + `t5 (requirement intelligence)` + `u6/v7 (JSONB alignment)`. Publishing only `w8/x9` without `s4-v7` breaks `alembic history/upgrade head` (missing parent) and `app/models/__init__.py` + `app/api/v1/routes.py` imports. Minimal coherent boundary is **Google Login + shared auth/rate-limit/session + F5 + F6 + migrations s4-x9**.

## Included files

**Modified 43:** `.env.example`, `.github/workflows/validation.yml`, `.gitignore`, `README.md`, `alembic/env.py`, `app/api/v1/endpoints/{auth,deal_pipeline_stage,lead,operational_dashboard,organization,requirement_candidate_conversion,warehouse,warehouse_intelligence_conversion,warehouse_match}.py`, `app/api/v1/routes.py`, `app/core/{config,security}.py`, `app/dependencies.py`, `app/main.py`, `app/models/{__init__,requirement,user}.py`, `app/repositories/{requirement_candidate_conversion,warehouse_intelligence_conversion,warehouse_match}.py`, `app/schemas/user.py`, `app/services/{deal,decision_maker_relevance,requirement_candidate_conversion,response_qualification}.py`, `docs/{RELEASE_READINESS,api/API_CONTRACT,operations/BACKUP_AND_RECOVERY,operations/DEPLOYMENT}.md`, `requirements.txt`, `tests/test_{config,deal,end_to_end_workflow,opportunity_workflow,organization_access,requirement_candidate_conversion,warehouse_matching_engine,warehouse_matching_intelligence}.py`

**Untracked added (required deps, 50 + frontend 59):** `alembic/versions/{s4,t5,u6,v7,w8,x9}.py`, `app/api/v1/endpoints/{f5_company_intelligence,requirement_intelligence}.py`, `app/core/rate_limit.py`, `app/models/{f5_company_intelligence,google_login_challenge,rate_limit,requirement_intelligence}.py`, `app/schemas/{f5,requirement}_intelligence.py`, `app/services/{f5_company_intelligence,google_auth,requirement_intelligence}.py`, `frontend/` (package.json/lock, vite/tsconfig, src/api/client*, src/components/GoogleSignIn*, src/pages/LoginPage/F5CompaniesPage etc., routing/Playwright), `tests/{conftest,test_auth_rate_limit,test_browser_transport,test_company_detail_acceptance,test_f5_*,test_google_auth,test_requirement_intelligence,test_security_audit,test_session_revocation}.py`, `docs/architecture/F5_COMPATIBILITY_BOUNDARY.md`, `docs/audits/BWIP_F6_*` + `BWIP_F7_*_2026-10-11.md` (plus preserved `BWIP_F7_OWNER_DECISIONS_APPROVED_2026-10-12.md`), and `candidate/.env` (copied from original `.env` for `ready` check — NOT committed, .gitignored).


**Excluded (117 untracked left in original):** evidence dumps docs/development/evidence/2026-10-1*, BWIP_COMPLETE_PROJECT_AUDIT, F7_SCOPE_PROPOSAL, .qa*, _build_f7.py, scripts fragments/verify/seed, frontend/test-results/ -- no runtime code excluded.

## Root causes / fixes (promoted from worktree)
Auth: SECRET_KEY>=32 even in dev, GOOGLE_CLIENT_ID + rate-limit + CORS_ORIGINS; bcrypt 72B/NULL guard, PyJWT require[exp,sub], ver:0; token_version check; PasswordInput; /google/config|challenge|login + require_google_origin + ver claim + logout/change-password/revoke/me; CORSMiddleware allow_credentials=False; Session(bind) HMAC + atomic upsert; single-use challenge hash + 5s timeout + email_verified + const-time nonce + no auto-merge; alembic casefold; google-auth/PyJWT. Tenant isolation: require_organization_access/write + limit_expensive_operation + cross-tenant checks. F5/F6: FACT/INFERENCE/UNKNOWN + freshness/verification + tenant checks via routes.py.

## Validation
Alembic: history linear to x9 (head), heads single x9, upgrade --sql head renders all 6 revisions. check passes with SECRET_KEY (was missing candidate/.env, fixed). Backend: SECRET_KEY=... pytest -q 845 passed, 6086 warnings (utcnow); targeted 88 passed; readiness 3 passed after .env. Frontend: npm ci 104, vitest 20 passed, tsc pass, vite build pass (59 modules 298kB).

## Security & next action
Token sessionStorage mitigated by 60m expiry + token_version + credentials omit + exact CORS; HttpOnly deferred. Google disabled when GOOGLE_CLIENT_ID empty (503). Candidate dependency-complete and test-green; original worktree preserved at a32bf6b; remote at 4ed75a9 (F7 doc). Publish FF only (never --force); if remote moved beyond 4ed75a9 rebase first. Staging Google browser flow BLOCKED (no CLIENT_ID/account) -- run after push.
