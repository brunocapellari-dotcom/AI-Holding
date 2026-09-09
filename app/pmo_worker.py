from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from types import TracebackType
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from app.schemas.api import ExecutionKind

DEFAULT_AUDIENCE = "holding-control-plane"
DEFAULT_AGENT_KEY = "PMO_IA"
SUPPORTED_EXECUTION_KINDS = (ExecutionKind.control_plane_health,)
REQUEST_TIMEOUT_SECONDS = 20.0
MAX_ERROR_LENGTH = 8000
MAX_DIAGNOSTIC_BODY_LENGTH = 2000

TokenProvider = Callable[[str], str]
Executor = Callable[["ControlPlaneClient", dict[str, Any]], dict[str, object]]


@dataclass(frozen=True)
class WorkerConfig:
    control_plane_url: str
    audience: str = DEFAULT_AUDIENCE
    agent_key: str = DEFAULT_AGENT_KEY
    max_tasks: int = 1

    @classmethod
    def from_env(cls) -> WorkerConfig:
        url = os.getenv("CONTROL_PLANE_URL", "").rstrip("/")
        if not url.startswith("https://"):
            raise RuntimeError("CONTROL_PLANE_URL must be an https URL")

        try:
            max_tasks = int(os.getenv("PMO_MAX_TASKS", "1"))
        except ValueError as exc:
            raise RuntimeError("PMO_MAX_TASKS must be an integer") from exc
        if not 1 <= max_tasks <= 10:
            raise RuntimeError("PMO_MAX_TASKS must be between 1 and 10")

        return cls(
            control_plane_url=url,
            audience=os.getenv("CONTROL_PLANE_AUDIENCE", DEFAULT_AUDIENCE),
            agent_key=os.getenv("PMO_AGENT_KEY", DEFAULT_AGENT_KEY),
            max_tasks=max_tasks,
        )


def google_identity_token(audience: str) -> str:
    token: object = id_token.fetch_id_token(  # type: ignore[no-untyped-call]
        Request(), audience
    )
    if not isinstance(token, str) or not token:
        raise RuntimeError("Google identity token provider returned an invalid token")
    return token


class ControlPlaneClient:
    def __init__(
        self,
        config: WorkerConfig,
        *,
        token_provider: TokenProvider = google_identity_token,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        token = token_provider(config.audience)
        bearer = f"Bearer {token}"
        self._client = httpx.Client(
            base_url=config.control_plane_url,
            headers={
                # Cloud Run validates X-Serverless-Authorization at the IAM boundary.
                # The regular Authorization header is preserved for the Control Plane,
                # which independently verifies the same Google identity token and binds
                # its subject to the canonical agent identity.
                "Authorization": bearer,
                "X-Serverless-Authorization": bearer,
                "User-Agent": "ai-holding-pmo-worker/1.0",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
        )

    def __enter__(self) -> ControlPlaneClient:
        self._client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._client.__exit__(exc_type, exc_value, traceback)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int | float | bool | None] | None = None,
        json_body: object | None = None,
    ) -> httpx.Response:
        response = self._client.request(
            method,
            path,
            params=params,
            json=json_body,
        )
        response.raise_for_status()
        return response

    def resolve_agent_id(self) -> str:
        agents = self._request("GET", "/api/v1/agents", params={"limit": 500}).json()
        for agent in agents:
            if agent.get("key") == self.config.agent_key:
                return str(agent["id"])
        raise RuntimeError(f"canonical agent {self.config.agent_key} was not found")

    def claim(self, agent_id: str) -> dict[str, Any] | None:
        response = self._client.post(
            "/api/v1/pmo/claim",
            json={
                "agent_id": agent_id,
                "execution_kinds": [item.value for item in SUPPORTED_EXECUTION_KINDS],
            },
        )
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return dict(response.json())

    def transition_run(
        self,
        run_id: str,
        status: str,
        *,
        output_metadata: dict[str, object] | None = None,
        error: str | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "status": status,
            "output_metadata": output_metadata or {},
        }
        if error is not None:
            payload["error"] = error[:MAX_ERROR_LENGTH]
        self._request(
            "POST",
            f"/api/v1/runs/{run_id}/transition",
            json_body=payload,
        )

    def transition_task(
        self,
        task_id: str,
        status: str,
        *,
        blocked_reason: str | None = None,
    ) -> None:
        payload: dict[str, object] = {"status": status}
        if blocked_reason is not None:
            payload["blocked_reason"] = blocked_reason[:MAX_ERROR_LENGTH]
        self._request(
            "POST",
            f"/api/v1/tasks/{task_id}/transition",
            json_body=payload,
        )

    def create_incident(
        self,
        *,
        project_id: str,
        title: str,
        details: dict[str, object],
    ) -> None:
        self._request(
            "POST",
            "/api/v1/incidents",
            json_body={
                "project_id": project_id,
                "severity": "sev3",
                "title": title[:240],
                "source": "pmo-worker",
                "details": details,
            },
        )

    def health_evidence(self) -> dict[str, object]:
        evidence: dict[str, object] = {}
        for path in ("/healthz", "/readyz"):
            response = self._request("GET", path)
            try:
                body: object = response.json()
            except json.JSONDecodeError:
                body = response.text[:1000]
            evidence[path] = {
                "status_code": response.status_code,
                "body": body,
            }
        return evidence


def execute_control_plane_health(
    client: ControlPlaneClient,
    task: dict[str, Any],
) -> dict[str, object]:
    return {
        "execution_kind": ExecutionKind.control_plane_health.value,
        "task_key": str(task.get("key", "")),
        "evidence": client.health_evidence(),
    }


EXECUTORS: dict[ExecutionKind, Executor] = {
    ExecutionKind.control_plane_health: execute_control_plane_health,
}


def _execution_kind(task: dict[str, Any]) -> ExecutionKind:
    raw = task.get("execution_kind")
    if not isinstance(raw, str):
        raise RuntimeError(f"unsupported task execution kind: {raw!r}")
    try:
        return ExecutionKind(raw)
    except ValueError as exc:
        raise RuntimeError(f"unsupported task execution kind: {raw!r}") from exc


def process_claim(client: ControlPlaneClient, claim: dict[str, Any]) -> None:
    task = dict(claim["task"])
    run = dict(claim["run"])
    task_id = str(task["id"])
    run_id = str(run["id"])
    project_id = str(task["project_id"])

    client.transition_run(run_id, "running")
    try:
        kind = _execution_kind(task)
        executor = EXECUTORS.get(kind)
        if executor is None:
            raise RuntimeError(f"worker does not implement execution kind {kind.value}")
        output = executor(client, task)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_LENGTH]
        client.transition_run(run_id, "failed", error=error)
        client.transition_task(task_id, "blocked", blocked_reason=error)
        with suppress(Exception):
            client.create_incident(
                project_id=project_id,
                title=f"PMO worker failed task {task.get('key', task_id)}",
                details={
                    "task_id": task_id,
                    "run_id": run_id,
                    "execution_kind": task.get("execution_kind"),
                    "error": error,
                },
            )
        raise

    client.transition_run(run_id, "succeeded", output_metadata=output)
    client.transition_task(task_id, "review")


def run_once(
    config: WorkerConfig,
    *,
    token_provider: TokenProvider = google_identity_token,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, int]:
    processed = 0
    with ControlPlaneClient(
        config,
        token_provider=token_provider,
        transport=transport,
    ) as client:
        agent_id = client.resolve_agent_id()
        for _ in range(config.max_tasks):
            claim = client.claim(agent_id)
            if claim is None:
                break
            process_claim(client, claim)
            processed += 1
    return {"processed": processed}


def _http_error_diagnostic(exc: httpx.HTTPStatusError) -> dict[str, object]:
    return {
        "event": "pmo_worker_http_error",
        "method": exc.request.method,
        "path": exc.request.url.path,
        "status_code": exc.response.status_code,
        "response": exc.response.text[:MAX_DIAGNOSTIC_BODY_LENGTH],
    }


def main() -> None:
    try:
        result = run_once(WorkerConfig.from_env())
    except httpx.HTTPStatusError as exc:
        print(json.dumps(_http_error_diagnostic(exc), sort_keys=True), file=sys.stderr)
        raise
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
