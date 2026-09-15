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