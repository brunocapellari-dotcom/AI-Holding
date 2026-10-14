# AI Holding — PostgreSQL local backup and restore drill (ZERO_COST)

The Holding Control Plane uses PostgreSQL for durable operational state. This
utility adds a local, runner-independent **logical database backup** with
integrity verification and a non-destructive restoration drill. It uses the
official, locally installed `pg_dump`, `pg_restore`, `createdb`, `psql` and
`dropdb` commands. No paid cloud product is required.

## Security preconditions

- Set `PGHOST` to `127.0.0.1` (or approved local Unix socket) and
  `PGDATABASE` to the actual Holding database. Remote hosts, `PGHOSTADDR`
  and PostgreSQL service overrides are blocked.
- Provide authorized connection secrets through the operating-system
  PostgreSQL credentials mechanism or environment, **never in command flags,
  Git, logs, or chat**.
- Use a **separate encrypted local disk/volume** with restrictive access.
  The script does not encrypt data. The confirmation flag is only an operator
  attestation of encryption; backup archives may contain sensitive information.
- Set `HOLDING_BACKUP_HMAC_KEY` to an independently stored hex-encoded random
  key of at least 32 bytes. This protects against unnoticed modification but
  does **not** encrypt the archive.
- Verify sufficient free disk space; ensure the installed PostgreSQL client
  utilities are compatible with the server version.

## Commands

```bash
python scripts/backup_local_postgres.py backup \
  --destination /encrypted-drive/holding-backup-001 \
  --encrypted-destination-confirmed

python scripts/backup_local_postgres.py verify \
  --snapshot /encrypted-drive/holding-backup-001

python scripts/backup_local_postgres.py restore-drill \
  --snapshot /encrypted-drive/holding-backup-001 \
  --target-db holding_restore_20261013
```

Backup opens a read-only `REPEATABLE READ` transaction, exports its snapshot,
fingerprints every user table in that snapshot (row count plus an
order-independent SHA-256 over the row text, rendered with pinned
`TimeZone`/`DateStyle`/float settings) and runs `pg_dump --snapshot=<id>` on the
very same snapshot, so the fingerprint describes exactly the archived data. It
uses a temporary staging directory, checks dump readability with
`pg_restore --list`, hashes the archive and authenticates the manifest
(archive SHA-256 + table fingerprint, format version 2) using HMAC. An existing
destination is never overwritten.

The drill refuses arbitrary database names or the configured source database.
It creates a fresh, isolated `holding_restore_*` database, restores with
`--single-transaction --exit-on-error`, checks that the Holding projects
table exists, recomputes the table fingerprint on the restored database and
fails unless every table (including `alembic_version` and
`hermes_event_receipts`) matches the signed manifest exactly, and drops
**only the database created by that drill** (also on failure). Failure to
create the new database never triggers a drop.

The drill proves logical data integrity of one snapshot; it is **not complete
business-data recovery certification**: point-in-time semantics (WAL/PITR),
roles, RPO/RTO and business workflows still need separate review
before declaring a final production recovery gate passed.

## Release evidence required

The branch needs local Python test execution (`pytest tests/test_backup_local_postgres.py`),
a real backup from the authorized PostgreSQL instance, verified HMAC and
checksums, a successful isolated restore, and recorded evidence in the
Holding release ledger. GitHub-hosted runners are not required and a PR alone
does not count as backup readiness.
