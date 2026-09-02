from __future__ import annotations

import sys
from enum import IntEnum, StrEnum

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError, SQLAlchemyError

from alembic import command
from app.db.session import engine


class MigrationExitCode(IntEnum):
    ok = 0
    public_schema_create_denied = 20
    database_connectivity_or_auth = 21
    migration_sql_error = 22
    migration_integrity_error = 23
    migration_database_error = 24
    unexpected_runtime_error = 25


class ProbeMode(StrEnum):
    connect = "probe-connect"
    schema_create = "probe-schema-create"


def _preflight_connectivity() -> bool:
    with engine.connect() as connection:
        return bool(connection.scalar(text("SELECT 1")) == 1)


def _preflight_public_schema() -> bool:
    with engine.connect() as connection:
        can_create = connection.scalar(
            text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
        )
    return can_create is True


def run_probe(mode: ProbeMode) -> bool:
    try:
        if mode == ProbeMode.connect:
            return _preflight_connectivity()
        return _preflight_public_schema()
    except Exception:
        return False


def run_migrations() -> MigrationExitCode:
    try:
        if not _preflight_public_schema():
            return MigrationExitCode.public_schema_create_denied
    except OperationalError:
        return MigrationExitCode.database_connectivity_or_auth
    except SQLAlchemyError:
        return MigrationExitCode.migration_database_error
    except Exception:
        return MigrationExitCode.unexpected_runtime_error

    try:
        command.upgrade(Config("alembic.ini"), "head")
    except OperationalError:
        return MigrationExitCode.database_connectivity_or_auth
    except ProgrammingError:
        return MigrationExitCode.migration_sql_error
    except IntegrityError:
        return MigrationExitCode.migration_integrity_error
    except SQLAlchemyError:
        return MigrationExitCode.migration_database_error
    except Exception:
        return MigrationExitCode.unexpected_runtime_error

    return MigrationExitCode.ok


def main() -> None:
    if len(sys.argv) == 2:
        try:
            probe = ProbeMode(sys.argv[1])
        except ValueError:
            raise SystemExit(int(MigrationExitCode.unexpected_runtime_error)) from None
        raise SystemExit(0 if run_probe(probe) else 1)

    raise SystemExit(int(run_migrations()))


if __name__ == "__main__":
    main()
