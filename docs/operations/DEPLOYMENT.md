# BWIP Deployment Runbook

This runbook describes the minimum controlled deployment procedure for the
BWIP pilot. It does not provision cloud infrastructure, TLS, backups, or
monitoring.

## Required services

- PostgreSQL compatible with the versions supported by the pinned SQLAlchemy
  and psycopg2 dependencies.
- A TLS-terminating reverse proxy or managed ingress.
- A secret store for `DATABASE_URL` and `SECRET_KEY`.

Do not put production credentials in the image, repository, or a committed
environment file.

## Configuration

Set these values through the deployment environment:

```text
APP_ENV=production
DEBUG=False
SECRET_KEY=<random value of at least 32 characters>
DATABASE_URL=postgresql://<least-privileged-user>:<password>@<private-host>:5432/<database>
```

The application rejects unsafe staging and production settings at startup.

## Release procedure

1. Confirm the application image was built from the reviewed commit.
2. Take and verify a fresh PostgreSQL backup before schema changes.
3. Validate the migration chain against a disposable PostgreSQL database.
4. Apply migrations from a release job or controlled maintenance step:

   ```powershell
   python -m alembic upgrade head
   ```

5. Start the application with the production ASGI command:

   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   The Docker image uses this command by default.
6. Route liveness checks to `/health` and traffic readiness checks to `/ready`.
7. Confirm authentication, organization isolation, and the core pilot workflow
   before allowing trusted pilot users to enter real data.

## Rollback and failure handling

Do not use `alembic downgrade` as the normal production rollback mechanism.
Keep the previous application image available, stop traffic if necessary, and
restore a verified backup into a disposable target first. For schema defects,
prefer a reviewed forward corrective migration. See
[`BACKUP_AND_RECOVERY.md`](BACKUP_AND_RECOVERY.md).

## Current limitations

This repository does not provide TLS, cloud provisioning, automated backups,
monitoring, alerting, database failover, or a live PostgreSQL release test.
Those controls must be supplied and verified by the deployment operator.

## 2026-10-10 durable auth and quotas

Forward head `w8b9c0d1e2f3` adds users.token_version and rate_limit_buckets.
Apply reviewed migrations in the release job before starting the new build.
No production migration was applied during the local audit.

Every application instance must use the same PostgreSQL database and private
signing key. Logout, password changes and administrator revocation increment
the durable account version; old credentials fail on subsequent requests,
including after worker restart. Logout intentionally affects all account
sessions. Already authorized in-flight requests are not cancelled. There are
no refresh tokens or public reset-email flows.

Quotas use atomic PostgreSQL upserts and the database clock, independent of
commercial transactions. Defaults: AUTH_RATE_LIMIT=20 per 60 seconds per client
IP (shared login/register/change-password budget); EXPENSIVE_RATE_LIMIT=30 per
60 seconds per account (dashboard and warehouse recommendation/generation).
Window settings are AUTH_RATE_WINDOW_SECONDS and EXPENSIVE_RATE_WINDOW_SECONDS.
Counter keys are HMAC digests. Expired rows are cleaned during quota requests.
Quota storage failure rejects work with 503, not a process-local fallback.
Monitor quota latency/size and 429/503 responses. No new paid service is required.

Set CORS_ORIGINS to a JSON array of exact frontend origins through the deployment
environment. Default remains localhost:5173. Use HTTPS for public traffic and
an HTTPS VITE_API_BASE_URL in the frontend deployment; VITE settings are public.

For direct local serving use `--no-proxy-headers`. Behind an ingress explicitly
configure Uvicorn's forwarded-allow-ips to that trusted ingress only, have the
ingress replace caller forwarding headers, and block direct backend access.
Never trust arbitrary forwarding headers or use an unrestricted proxy allowlist.
Local QA verified spoofed headers with proxy handling disabled; deployed proxy
identity/rate behavior still needs separate verification. Shared DB limits do
not replace ingress connection/body limits, DDoS protection or load tests.

The browser uses tab-scoped sessionStorage for the existing bearer token and
omits cookie credentials. Reload preserves the session; a new independent tab
requires sign-in. Existing localStorage credentials are removed without being
migrated; users must sign in again. Logout still revokes all account sessions.
This limits persistence but does not prevent XSS token theft. Public launch
requires an explicit session-risk decision and deployed CSP verification; see
the 2026-10-11 acceptance review and cookie-session migration proposal in
`docs/development/BWIP_COMPLETE_PROJECT_AUDIT.md`. This runbook is intended configuration,
not evidence of cloud TLS, IAM, encryption, private DB or secret-store behavior.
