# BWIP Backup and Recovery

This document is an operator procedure, not an automated backup system.

## Backup policy

- Take an encrypted PostgreSQL backup at least daily.
- During active pilot data entry, use a shorter interval if a day's work cannot
  be recreated manually.
- Store an encrypted copy outside the database host.
- Retain daily backups for at least 30 days, subject to the organization's
  retention policy.
- Before every migration release, record the current Alembic revision and take
  a fresh backup.
- Never commit backups, dumps, credentials, or encryption keys to Git.

The operator must configure the backup scheduler, encryption key management,
off-host storage, and alerting separately.

## Restore drill

Perform at least monthly and after material infrastructure changes:

1. Provision a disposable PostgreSQL instance.
2. Restore the selected backup into that instance.
3. Verify database integrity, table counts, and the Alembic revision.
4. Point a matching application build at the disposable database.
5. Verify startup, `/health`, `/ready`, authentication, organization isolation,
   and representative warehouse-to-deal workflow records.
6. Record the backup identifier, restore time, observed errors, validation
   results, and operator.
7. Destroy the disposable instance and any temporary credentials.

Do not call a backup recoverable until this drill succeeds.

## Migration recovery

Use this sequence when a migration release fails:

1. Stop or isolate application traffic as appropriate.
2. Preserve logs and record the database revision and release image.
3. Restore the pre-release backup into a disposable database first.
4. Reproduce and diagnose the failure without changing the original backup.
5. Prepare a reviewed forward corrective migration or a corrected application
   release.
6. Validate the correction against disposable PostgreSQL.
7. Apply the corrected release to the production recovery target during a
   controlled window.
8. Verify readiness and key business records before reopening pilot access.

Production restore, failover, and migration recovery have not been exercised
by this repository and remain deployment-owner responsibilities.

## Local synthetic rehearsal (2026-10-10)

`python -m scripts.verify_followup_runtime --backup-only` creates an isolated
source database and a distinct empty restoration database. It uses PostgreSQL
17 pg_dump custom format and pg_restore with --no-owner/--no-acl, validates the
head/schema and every public table's row count, checks commercial relationships
and tenant ownership, starts the restored application, tests login/readiness,
foreign-tenant denial and a legitimate matching write. It removes exactly its
own databases and temporary synthetic archive. BWIP_PG_BIN can specify the
local PostgreSQL client directory.

Results/timing: docs/development/evidence/2026-10-10/backup-restore.json. This
archive contains synthetic records only and is temporarily unencrypted. It
does not test the operator's encrypted/off-host backup service, key recovery,
retention or storage permissions. Those controls remain BLOCKED. The measured
time is a local observation, not an adopted RTO/RPO. Real data must follow the
encrypted backup policy above and must never be placed in this QA fixture.
