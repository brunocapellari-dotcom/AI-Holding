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
