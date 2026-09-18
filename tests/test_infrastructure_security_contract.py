from pathlib import Path

TERRAFORM_ROOT = Path("infra/terraform")


def _read(name: str) -> str:
    return (TERRAFORM_ROOT / name).read_text(encoding="utf-8")


def test_cloud_sql_remains_private_encrypted_and_destroy_protected() -> None:
    main = _read("main.tf")
    assert 'ipv4_enabled                                  = false' in main
    assert 'ssl_mode                                      = "ENCRYPTED_ONLY"' in main
    assert 'deletion_protection = true' in main
    assert 'prevent_destroy = true' in main


def test_migration_job_uses_dedicated_runtime_identity() -> None:
    main = _read("main.tf")
    migration_start = main.index('resource "google_cloud_run_v2_job" "migrate"')
    migration_block = main[migration_start:]

    assert "service_account = google_service_account.migration.email" in migration_block
    assert "google_service_account_iam_member.deployer_act_as_migration" in migration_block
    assert "google_secret_manager_secret_iam_member.migration_database_url_rollback" in (
        migration_block
    )


def test_database_iam_defines_separate_api_and_migration_principals() -> None:
    database_iam = _read("database_iam.tf")
    assert 'resource "google_sql_user" "control_plane_iam"' in database_iam
    assert 'resource "google_sql_user" "migration_iam"' in database_iam
    assert 'account_id   = "holding-db-migration"' in database_iam
    assert 'role    = "roles/cloudsql.client"' in database_iam
    assert 'role    = "roles/cloudsql.instanceUser"' in database_iam


def test_terraform_never_grants_public_iam_membership() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(TERRAFORM_ROOT.glob("*.tf"))
    )
    assert "allUsers" not in combined
    assert "allAuthenticatedUsers" not in combined


def test_password_database_secret_is_explicitly_rollback_only_for_migration_identity() -> None:
    database_iam = _read("database_iam.tf")
    assert 'resource "google_secret_manager_secret_iam_member" "migration_database_url_rollback"' in (
        database_iam
    )


def test_worker_recurrence_uses_cloud_scheduler_not_github_actions() -> None:
    scheduler = _read("scheduler.tf")
    assert 'resource "google_cloud_scheduler_job" "pmo_worker"' in scheduler
    assert 'resource "google_cloud_scheduler_job" "knowledge_worker"' in scheduler
    assert "https://run.googleapis.com/v2/projects/" in scheduler
    assert "oauth_token" in scheduler
    assert "github_main_scheduler_principal" not in scheduler
    assert not Path(".github/workflows/autonomous-workers.yml").exists()


def test_cloud_scheduler_identity_is_only_job_invoker_in_scheduler_contract() -> None:
    scheduler = _read("scheduler.tf")
    assert scheduler.count('role     = "roles/run.invoker"') == 2
    assert "roles/run.admin" not in scheduler
    assert "roles/editor" not in scheduler
    assert "roles/owner" not in scheduler


def test_github_collector_is_secret_gated_and_disabled_by_default() -> None:
    collector = _read("github_collector.tf")
    assert 'variable "github_collector_enabled"' in collector
    assert "default     = false" in collector
    assert 'variable "github_collector_token_secret_id"' in collector
    assert 'data "google_secret_manager_secret" "github_collector_token"' in collector
    assert "GITHUB_TOKEN" in collector
    assert "roles/secretmanager.secretAccessor" in collector
    assert 'service_account = google_service_account.pmo_worker.email' in collector
    assert 'resource "google_cloud_scheduler_job" "github_collector"' in collector
    assert "github.com/" not in collector
    assert "ghp_" not in collector
    assert "github_pat_" not in collector


def test_audit_events_have_postgresql_append_only_trigger_migration() -> None:
    migration = Path("alembic/versions/0018_audit_immutability.py").read_text(encoding="utf-8")
    assert "BEFORE UPDATE OR DELETE ON audit_events" in migration
    assert "audit_events is append-only" in migration
    assert 'bind.dialect.name != "postgresql"' in migration
