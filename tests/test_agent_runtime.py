from typing import Any

import pytest
from fastapi import FastAPI

from services.agent_runtime import runtime as runtime_module
from services.agent_runtime.runtime import AgentRuntimeConfig, compose_agent_runtime


def _config(*, enabled: bool, environment: str = "test") -> AgentRuntimeConfig:
    return AgentRuntimeConfig(
        enabled=enabled,
        environment=environment,
        database_url="postgresql+psycopg://holding:holding@localhost:5432/holding_test",
        db_schema="agentos_test",
        scheduler_enabled=True,
        durable_queue_enabled=True,
        port=8080,
    )


def test_disabled_runtime_returns_control_plane_unchanged() -> None:
    base_app = FastAPI()
    assert compose_agent_runtime(base_app, _config(enabled=False)) is base_app


def test_production_runtime_requires_jwt_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_VERIFICATION_KEY", raising=False)
    monkeypatch.delenv("JWT_JWKS_FILE", raising=False)

    with pytest.raises(RuntimeError, match="requires JWT_VERIFICATION_KEY"):
        compose_agent_runtime(FastAPI(), _config(enabled=True, environment="production"))


def test_enabled_runtime_preserves_base_app_and_uses_durable_separate_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    base_app = FastAPI()

    class FakeDb:
        def __init__(self, **kwargs: Any) -> None:
            captured["db"] = kwargs

    class FakeAgentOS:
        def __init__(self, **kwargs: Any) -> None:
            captured["agentos"] = kwargs

        def get_app(self) -> FastAPI:
            return captured["agentos"]["base_app"]

    monkeypatch.setattr(runtime_module, "PostgresDb", FakeDb)
    monkeypatch.setattr(runtime_module, "AgentOS", FakeAgentOS)

    composed = compose_agent_runtime(base_app, _config(enabled=True))

    assert composed is base_app
    assert captured["db"]["db_schema"] == "agentos_test"
    assert captured["db"]["create_schema"] is True
    assert captured["agentos"]["base_app"] is base_app
    assert captured["agentos"]["on_route_conflict"] == "preserve_base_app"
    assert captured["agentos"]["scheduler"] is True
    assert captured["agentos"]["authorization"] is False
    assert captured["agentos"]["telemetry"] is False
    queue = captured["agentos"]["queue"]
    assert queue.durable is True
    assert queue.max_attempts == 2
