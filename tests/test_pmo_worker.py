import json

import httpx
import pytest

from app.pmo_worker import (
    STAGE_EXIT_CODES,
    WorkerConfig,
    WorkerStage,
    WorkerStageError,
    _stage_error_diagnostic,
    _worker_exit_code,
    run_once,
)

AGENT_ID = "11111111-1111-1111-1111-111111111111"
PROJECT_ID = "22222222-2222-2222-2222-222222222222"
TASK_ID = "33333333-3333-3333-3333-333333333333"
RUN_ID = "44444444-4444-4444-4444-444444444444"


def claim_payload() -> dict[str, object]:
    return {
        "task": {
            "id": TASK_ID,
            "key": "CONTROL_PLANE_HEALTH",
            "project_id": PROJECT_ID,
            "execution_kind": "control_plane_health",
        },
        "run": {
            "id": RUN_ID,
            "task_id": TASK_ID,
            "agent_id": AGENT_ID,
            "status": "queued",
        },
    }


def test_worker_completes_bounded_health_execution_and_sends_evidence():
    requests: list[tuple[str, str, dict[str, object] | None]] = []
    claim_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal claim_count
        body = json.loads(request.content) if request.content else None
        requests.append((request.method, request.url.path, body))
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["X-Serverless-Authorization"] == "Bearer test-token"

        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            assert body == {"execution_kinds": ["control_plane_health"]}
            claim_count += 1
            if claim_count == 1:
                return httpx.Response(200, json=claim_payload())
            return httpx.Response(204)
        if request.method == "GET" and request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.method == "GET" and request.url.path == "/ready":
            return httpx.Response(200, json={"status": "ready"})
        return httpx.Response(200, json={"ok": True})

    result = run_once(
        WorkerConfig(
            control_plane_url="https://holding.example",
            max_tasks=2,
        ),
        token_provider=lambda audience: "test-token",
        transport=httpx.MockTransport(handler),
    )

    assert result == {"processed": 1}
    assert not any(path == "/api/v1/agents" for _, path, _ in requests)
    run_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/runs/{RUN_ID}/transition"
    ]
    assert run_transitions[0] == {"status": "running", "output_metadata": {}}
    assert run_transitions[1]["status"] == "succeeded"
    output = run_transitions[1]["output_metadata"]
    assert output["execution_kind"] == "control_plane_health"
    assert output["evidence"]["/health"]["status_code"] == 200
    assert output["evidence"]["/ready"]["status_code"] == 200

    task_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/tasks/{TASK_ID}/transition"
    ]
    assert task_transitions == [{"status": "review"}]


def test_worker_ready_failure_has_specific_stage_and_records_safe_incident():
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        requests.append((request.method, request.url.path, body))
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            return httpx.Response(200, json=claim_payload())
        if request.method == "GET" and request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.method == "GET" and request.url.path == "/ready":
            return httpx.Response(503, json={"status": "not-ready"})
        return httpx.Response(200, json={"ok": True})

    with pytest.raises(WorkerStageError) as caught:
        run_once(
            WorkerConfig(control_plane_url="https://holding.example"),
            token_provider=lambda audience: "test-token",
            transport=httpx.MockTransport(handler),
        )

    assert caught.value.stage == WorkerStage.ready
    assert isinstance(caught.value.cause, httpx.HTTPStatusError)
    assert STAGE_EXIT_CODES[caught.value.stage] == 47
    assert _worker_exit_code(caught.value) == 75

    run_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/runs/{RUN_ID}/transition"
    ]
    assert [item["status"] for item in run_transitions] == ["running", "failed"]
    assert run_transitions[1]["error"] == "ready:HTTPStatusError"

    task_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/tasks/{TASK_ID}/transition"
    ]
    assert task_transitions[0] == {
        "status": "blocked",
        "blocked_reason": "ready:HTTPStatusError",
    }

    incidents = [
        body for method, path, body in requests if method == "POST" and path == "/api/v1/incidents"
    ]
    assert len(incidents) == 1
    assert incidents[0]["project_id"] == PROJECT_ID
    assert incidents[0]["severity"] == "sev3"
    assert incidents[0]["details"]["task_id"] == TASK_ID
    assert incidents[0]["details"]["failure_stage"] == "ready"
    assert incidents[0]["details"]["path"] == "/ready"
    assert incidents[0]["details"]["status_code"] == 503
    assert "response" not in incidents[0]["details"]


def test_worker_health_failure_encodes_server_error_class():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            return httpx.Response(200, json=claim_payload())
        if request.method == "GET" and request.url.path == "/health":
            return httpx.Response(502, json={"status": "bad-gateway"})
        return httpx.Response(200, json={"ok": True})

    with pytest.raises(WorkerStageError) as caught:
        run_once(
            WorkerConfig(control_plane_url="https://holding.example"),
            token_provider=lambda audience: "test-token",
            transport=httpx.MockTransport(handler),
        )

    assert caught.value.stage == WorkerStage.health
    assert STAGE_EXIT_CODES[caught.value.stage] == 46
    assert _worker_exit_code(caught.value) == 65
    diagnostic = _stage_error_diagnostic(caught.value)
    assert diagnostic["exit_code"] == 65
    assert diagnostic["path"] == "/health"
    assert diagnostic["status_code"] == 502


def test_worker_health_failure_encodes_forbidden_class():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            return httpx.Response(200, json=claim_payload())
        if request.method == "GET" and request.url.path == "/health":
            return httpx.Response(403, json={"detail": "forbidden"})
        return httpx.Response(200, json={"ok": True})

    with pytest.raises(WorkerStageError) as caught:
        run_once(
            WorkerConfig(control_plane_url="https://holding.example"),
            token_provider=lambda audience: "test-token",
            transport=httpx.MockTransport(handler),
        )

    assert caught.value.stage == WorkerStage.health
    assert _worker_exit_code(caught.value) == 62
    assert _stage_error_diagnostic(caught.value)["status_code"] == 403


def test_worker_claim_failure_has_deterministic_stage_and_safe_diagnostic():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text='{"detail":"forbidden"}')

    with pytest.raises(WorkerStageError) as caught:
        run_once(
            WorkerConfig(control_plane_url="https://holding.example"),
            token_provider=lambda audience: "test-token",
            transport=httpx.MockTransport(handler),
        )

    assert caught.value.stage == WorkerStage.claim
    diagnostic = _stage_error_diagnostic(caught.value)
    assert diagnostic == {
        "event": "pmo_worker_stage_error",
        "stage": "claim",
        "exit_code": STAGE_EXIT_CODES[WorkerStage.claim],
        "cause_type": "HTTPStatusError",
        "method": "POST",
        "path": "/api/v1/pmo/claim",
        "status_code": 403,
        "response": '{"detail":"forbidden"}',
    }
    serialized = json.dumps(diagnostic)
    assert "test-token" not in serialized


def test_worker_identity_fetch_failure_has_deterministic_stage():
    def failed_token_provider(audience: str) -> str:
        raise RuntimeError("metadata unavailable")

    with pytest.raises(WorkerStageError) as caught:
        run_once(
            WorkerConfig(control_plane_url="https://holding.example"),
            token_provider=failed_token_provider,
        )

    assert caught.value.stage == WorkerStage.identity_fetch
    assert STAGE_EXIT_CODES[caught.value.stage] == 40
    assert _stage_error_diagnostic(caught.value)["cause_type"] == "RuntimeError"


def test_worker_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("CONTROL_PLANE_URL", raising=False)
    with pytest.raises(RuntimeError, match="https URL"):
        WorkerConfig.from_env()

    monkeypatch.setenv("CONTROL_PLANE_URL", "https://holding.example")
    monkeypatch.setenv("PMO_MAX_TASKS", "11")
    with pytest.raises(RuntimeError, match="between 1 and 10"):
        WorkerConfig.from_env()
