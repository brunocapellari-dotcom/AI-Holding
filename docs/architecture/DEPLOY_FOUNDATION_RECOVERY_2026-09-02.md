# Production foundation recovery

Date: 2026-09-02

## Incident

The production workflow attempted to complete a missing Cloud SQL foundation by running Terraform with `deploy_service=false`. Because the Cloud Run API service and migration job were already present in Terraform state, that variable changed both counted resources from `count=1` to `count=0`, which planned their destruction. `lifecycle.prevent_destroy` correctly blocked the operation before any destructive change occurred.

## Root cause

A bootstrap mode that changes the cardinality of already-managed runtime resources is unsafe once a partial deployment exists.

## Corrective action

Foundation recovery must target only the missing stateful database resources and their dependency graph. It must never disable or remove an already-managed runtime simply to bootstrap missing dependencies.

The workflow therefore uses a targeted Terraform apply only when the Cloud SQL instance is absent, targeting:

- `google_sql_database_instance.postgres`
- `google_sql_database.holding`
- `google_sql_user.holding`
- `google_secret_manager_secret_version.database_url`

Terraform includes their declared dependencies automatically. The normal full production plan then runs with `deploy_service=true` and the newly built immutable image.

## Security and safety properties

- Existing Cloud Run resources remain outside the bootstrap apply scope.
- `prevent_destroy` remains enabled; it is not weakened to bypass the failure.
- No static cloud credentials are introduced.
- The database remains private-IP only with encrypted connections, backups, PITR and deletion protection.
- The subsequent full Terraform plan is still authoritative for the complete production state.

## Reusable lesson

Never use a feature flag that reduces Terraform resource count as a recovery mechanism after those resources may already exist. For partial-infrastructure recovery, either split state/modules cleanly or constrain the bootstrap operation to the missing dependency set without changing existing resource cardinality.
