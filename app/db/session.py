from __future__ import annotations

import atexit
from collections.abc import Generator
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.engine import build_database_engine

engine, _cloud_sql_connector = build_database_engine(settings)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False)


def close_database_connector() -> None:
    global _cloud_sql_connector
    connector: Any | None = _cloud_sql_connector
    if connector is not None:
        connector.close()
        _cloud_sql_connector = None


atexit.register(close_database_connector)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
