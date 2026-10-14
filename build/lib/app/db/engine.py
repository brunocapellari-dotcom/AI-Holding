from __future__ import annotations

from collections.abc import Callable
from typing import Any

from google.cloud.sql.connector import Connector
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.core.config import Settings


def _required(value: str | None, name: str) -> str:
    if value is None or not value.strip():
        raise RuntimeError(f"{name} is required when DATABASE_AUTH_MODE=cloud_sql_iam")
    return value.strip()


def build_database_engine(
    app_settings: Settings,
    connector_factory: Callable[..., Any] = Connector,
) -> tuple[Engine, Any | None]:
    common: dict[str, object] = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "future": True,
    }

    if app_settings.database_auth_mode == "password":
        return create_engine(app_settings.database_url, **common), None

    instance = _required(
        app_settings.cloud_sql_instance_connection_name,
        "CLOUD_SQL_INSTANCE_CONNECTION_NAME",
    )
    user = _required(app_settings.cloud_sql_iam_user, "CLOUD_SQL_IAM_USER")
    connector = connector_factory(refresh_strategy="lazy")

    def get_connection() -> Any:
        return connector.connect(
            instance,
            "psycopg",
            user=user,
            db=app_settings.cloud_sql_database,
            ip_type=app_settings.cloud_sql_ip_type,
            enable_iam_auth=True,
        )

    engine = create_engine(
        "postgresql+psycopg://",
        creator=get_connection,
        **common,
    )
    return engine, connector
