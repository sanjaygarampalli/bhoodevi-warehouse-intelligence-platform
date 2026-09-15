# BWIP Release Readiness

This document describes the smallest safe operating baseline for the BWIP
pilot and distinguishes repository implementation from operational work that
must be performed by the deployment owner.

## Implemented in the application

- `/health` is a liveness endpoint and does not require database access.
- `/ready` executes a database connectivity check and returns `503` when the
  configured database cannot be reached.
- `APP_ENV=staging` or `APP_ENV=production` rejects startup when `DEBUG=True`,
  `SECRET_KEY` is shorter than 32 characters, the database is not PostgreSQL,
  or the database URL still contains the documented placeholder credentials.
- Secrets remain environment-provided and `.env` remains ignored by Git.
- No CORS middleware is currently configured. The API is therefore not
  claiming browser cross-origin support; if a separate browser frontend is
  introduced, configure an explicit origin allowlist before deployment.

## Required deployment procedure

1. Provision PostgreSQL and a least-privileged application database user.
2. Set `APP_ENV=production`, `DEBUG=False`, a unique random `SECRET_KEY`, and
   a private PostgreSQL `DATABASE_URL` through the deployment secret store.
3. Run `python -m alembic upgrade head` during a controlled release window.
4. Start the API with a production ASGI process, for example:
   `uvicorn app.main:app --host 0.0.0.0 --port 8000` behind a TLS-terminating
   reverse proxy or managed ingress.
5. Route load-balancer liveness checks to `/health` and traffic readiness
   checks to `/ready`.
6. Confirm logs, authentication, authorization, and organization-isolation
   regression checks before allowing real business users to connect.

No cloud deployment, managed database, TLS ingress, or automated backup
service is provisioned by this repository.

The minimum deployment and operational procedures are documented in
[`operations/DEPLOYMENT.md`](operations/DEPLOYMENT.md) and
[`operations/BACKUP_AND_RECOVERY.md`](operations/BACKUP_AND_RECOVERY.md).

## Backup and recovery recommendation

### Recommended operational procedure

- Take encrypted PostgreSQL backups at least daily; use a shorter interval
  during active pilot data entry if the business cannot recreate a day's work.
- Retain daily backups for 30 days and maintain an encrypted off-host copy.
- Perform a restore drill at least monthly into a disposable PostgreSQL
  instance and verify both data counts and application login/workflow access.
- Before migrations, take a fresh backup and record the current Alembic
  revision. Apply migrations forward only; do not use destructive downgrade
  commands as a recovery strategy.
- For recovery, provision a compatible application version, restore the
  database to a disposable target first, validate the revision and core
  workflow, then switch traffic using the deployment platform's rollback or
  DNS/ingress procedure.

### Not implemented by this repository

- Scheduled backups
- Backup encryption/key management
- Off-site retention
- Restore automation
- Monitoring/alerting integration
- Disaster-recovery failover

These must be supplied and tested by the operator before treating BWIP as a
production service.