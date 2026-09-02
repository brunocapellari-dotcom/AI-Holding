# Production database migration runbook

Date: 2026-09-02

Production migrations run inside the private VPC through the Cloud Run migration job. The deployment service account deliberately does not need Cloud Logging read access to identify the first-order database failure class.

The job executes `python -m app.db_migrate`. Before Alembic, the runner verifies that the connected database identity can create objects in the `public` schema. It then runs `alembic upgrade head` and exits with a stable code:

- `0`: migration completed.
- `20`: database connection works but the migration identity lacks `CREATE` on schema `public`.
- `21`: connection, authentication, TLS, or network-level database failure.
- `22`: SQL/programming failure while applying the migration.
- `23`: integrity constraint failure while applying the migration.
- `24`: another SQLAlchemy database failure.

The runner does not print the database URL, password, SQL parameters, or exception text. Cloud Run execution status exposes only the exit code needed to select the next recovery path.

## Security rule

Do not grant broad Cloud Logging access merely to debug a migration. Do not weaken Cloud SQL TLS, VPC isolation, `prevent_destroy`, deletion protection, or the production no-delete Terraform gate. If a migration requires DDL privileges that the runtime application should not retain, split migration and runtime database identities rather than permanently broadening the runtime role.
