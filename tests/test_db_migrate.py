from sqlalchemy.exc import OperationalError, ProgrammingError

from alembic import command
from app import db_migrate
from app.db_migrate import MigrationExitCode, ProbeMode


def test_migration_runner_succeeds_after_preflight(monkeypatch):
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(db_migrate, "_preflight_public_schema", lambda: True)

    def fake_upgrade(config, revision):
        calls.append((config.config_file_name, revision))

    monkeypatch.setattr(command, "upgrade", fake_upgrade)

    assert db_migrate.run_migrations() == MigrationExitCode.ok
    assert calls == [("alembic.ini", "head")]


def test_migration_runner_reports_missing_public_schema_create(monkeypatch):
    monkeypatch.setattr(db_migrate, "_preflight_public_schema", lambda: False)

    assert db_migrate.run_migrations() == MigrationExitCode.public_schema_create_denied


def test_migration_runner_reports_connectivity_failure(monkeypatch):
    def fail_preflight():
        raise OperationalError("SELECT 1", {}, Exception("connection failed"))

    monkeypatch.setattr(db_migrate, "_preflight_public_schema", fail_preflight)

    assert db_migrate.run_migrations() == MigrationExitCode.database_connectivity_or_auth


def test_migration_runner_reports_sql_failure(monkeypatch):
    monkeypatch.setattr(db_migrate, "_preflight_public_schema", lambda: True)

    def fail_upgrade(config, revision):
        raise ProgrammingError("CREATE TABLE", {}, Exception("permission denied"))

    monkeypatch.setattr(command, "upgrade", fail_upgrade)

    assert db_migrate.run_migrations() == MigrationExitCode.migration_sql_error


def test_connectivity_probe_uses_connectivity_preflight(monkeypatch):
    monkeypatch.setattr(db_migrate, "_preflight_connectivity", lambda: True)

    assert db_migrate.run_probe(ProbeMode.connect) is True


def test_schema_probe_uses_schema_preflight(monkeypatch):
    monkeypatch.setattr(db_migrate, "_preflight_public_schema", lambda: False)

    assert db_migrate.run_probe(ProbeMode.schema_create) is False


def test_probe_fails_closed_on_runtime_exception(monkeypatch):
    def fail_probe():
        raise RuntimeError("redacted")

    monkeypatch.setattr(db_migrate, "_preflight_connectivity", fail_probe)

    assert db_migrate.run_probe(ProbeMode.connect) is False
