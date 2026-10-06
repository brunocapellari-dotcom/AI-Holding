from __future__ import annotations

import os
from dataclasses import dataclass

from agno.db.postgres import PostgresDb
from agno.os import AgentOS, QueueConfig
from fastapi import FastAPI

from app.core.config import settings


@dataclass(frozen=True)
class AgentRuntimeConfig:
    enabled: bool
    environment: str
    database_url: str
    db_schema: str
    scheduler_enabled: bool
    durable_queue_enabled: bool
    port: int = 8080

    @classmethod
    def from_settings(cls) -> AgentRuntimeConfig:
        return cls(
            enabled=settings.agentos_enabled,
            environment=settings.environment,
            database_url=settings.database_url,
            db_schema=settings.agentos_db_schema,
            scheduler_enabled=settings.agentos_scheduler_enabled,
            durable_queue_enabled=settings.agentos_durable_queue_enabled,
            port=int(os.getenv("PORT", "8080")),
        )


def _production_jwt_configured() -> bool:
    return bool(os.getenv("JWT_VERIFICATION_KEY") or os.getenv("JWT_JWKS_FILE"))


def compose_agent_runtime(
    base_app: FastAPI,
    config: AgentRuntimeConfig | None = None,
) -> FastAPI:
    """Mount AgentOS around the existing Control Plane without weakening it.

    The legacy domain API remains authoritative during the strangler migration.
    AgentOS is opt-in and production activation fails closed unless JWT
    verification is explicitly configured.
    """

    runtime = config or AgentRuntimeConfig.from_settings()
    if not runtime.enabled:
        return base_app

    if runtime.environment == "production" and not _production_jwt_configured():
        raise RuntimeError(
            "AgentOS production activation requires JWT_VERIFICATION_KEY or JWT_JWKS_FILE"
        )

    db = PostgresDb(
        id="holding-agentos",
        db_url=runtime.database_url,
        db_schema=runtime.db_schema,
        create_schema=True,
    )
    queue = QueueConfig(
        durable=runtime.durable_queue_enabled,
        max_concurrency=8,
        max_queue_depth=1000,
        max_attempts=2,
    )
    agent_os = AgentOS(
        id="holding-agentos",
        description="Primary agent runtime for the AI Holding",
        agents=[],
        teams=[],
        workflows=[],
        db=db,
        queue=queue,
        scheduler=runtime.scheduler_enabled,
        scheduler_base_url=f"http://127.0.0.1:{runtime.port}",
        base_app=base_app,
        on_route_conflict="preserve_base_app",
        authorization=runtime.environment == "production",
        telemetry=False,
    )
    return agent_os.get_app()
