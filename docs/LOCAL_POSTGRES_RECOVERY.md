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

Backup uses a consistent `pg_dump` snapshot and a temporary staging directory,
checks dump readability with `pg_restore --list`, hashes the archive and
authenticates the manifest using HMAC. An existing destination is never overwritten.

The drill refuses arbitrary database names or the configured source database.
It creates a fresh, isolated `holding_restore_*` database, restores with
`--single-transaction --exit-on-error`, checks that the Holding projects
table exists, and drops **only the database created by that drill**. Failure to
create the new database never triggers a drop.

The drill is a minimum restore smoke, **not complete business-data recovery
certification**: project counts, Hermes receipts, migrations, point-in-time
semantics, roles, RPO/RTO and business workflows still need separate review
before declaring a final production recovery gate passed.

## Release evidence required

The branch needs local Python test execution (`pytest tests/test_backup_local_postgres.py`),
a real backup from the authorized PostgreSQL instance, verified HMAC and
checksums, a successful isolated restore, and recorded evidence in the
Holding release ledger. GitHub-hosted runners are not required and a PR alone
does not count as backup readiness.
