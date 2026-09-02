from __future__ import annotations

from enum import IntEnum

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


def _preflight_public_schema() -> bool:
    with engine.connect() as connection:
        can_create = connection.scalar(
            text("SELECT has_schema_privilege(current_user, 'public', 'CREATE')")
        )
    return can_create is True


def run_migrations() -> MigrationExitCode:
    try:
        if not _preflight_public_schema():
            return MigrationExitCode.public_schema_create_denied
    except OperationalError:
        return MigrationExitCode.database_connectivity_or_auth

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

    return MigrationExitCode.ok


def main() -> None:
    raise SystemExit(int(run_migrations()))


if __name__ == "__main__":
    main()
