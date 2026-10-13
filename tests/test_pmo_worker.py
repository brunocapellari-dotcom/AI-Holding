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
from app.schemas.api import ExecutionKind

AGENT_ID = "11111111-1111-1111-1111-111111111111"
PROJECT_ID = "22222222-2222-2222-2222-222222222222"
TASK_ID = "33333333-3333-3333-3333-333333333333"
RUN_ID = "44444444-4444-4444-4444-444444444444"


def claim_payload(
    execution_kind: str = "control_plane_health",
    task_key: str = "CONTROL_PLANE_HEALTH",
) -> dict[str, object]:
    return {
        "task": {
            "id": TASK_ID,
            "key": task_key,
            "project_id": PROJECT_ID,
            "execution_kind": execution_kind,
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


@pytest.mark.parametrize(
    ("execution_kind", "path", "task_key"),
    [
        (
            ExecutionKind.knowledge_gap_scan,
            "/api/v1/knowledge/gaps",
            "KNOWLEDGE_GAP_SCAN",
        ),
        (
            ExecutionKind.knowledge_outcome_review,
            "/api/v1/knowledge/outcome-review",
            "KNOWLEDGE_OUTCOME_REVIEW",
        ),
    ],
)
def test_worker_executes_read_only_knowledge_maintenance(
    execution_kind: ExecutionKind,
    path: str,
    task_key: str,
) -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        requests.append((request.method, request.url.path, body))
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            assert body == {"execution_kinds": [execution_kind.value]}
            return httpx.Response(
                200,
                json=claim_payload(execution_kind.value, task_key),
            )
        if request.method == "GET" and request.url.path == path:
            assert request.url.params["limit"] == "100"
            return httpx.Response(
                200,
                json=[
                    {"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"},
                    {"id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"},
                ],
            )
        return httpx.Response(200, json={"ok": True})

    result = run_once(
        WorkerConfig(
            control_plane_url="https://holding.example",
            execution_kinds=(execution_kind,),
        ),
        token_provider=lambda audience: "test-token",
        transport=httpx.MockTransport(handler),
    )

    assert result == {"processed": 1}
    run_transitions = [
        body
        for method, request_path, body in requests
        if method == "POST" and request_path == f"/api/v1/runs/{RUN_ID}/transition"
    ]
    output = run_transitions[1]["output_metadata"]
    assert output == {
        "execution_kind": execution_kind.value,
        "task_key": task_key,
        "candidate_count": 2,
        "claim_ids": [
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        ],
    }


def test_worker_rejects_invalid_knowledge_queue_shape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            return httpx.Response(
                200,
                json=claim_payload("knowledge_gap_scan", "KNOWLEDGE_GAP_SCAN"),
            )
        if request.method == "GET" and request.url.path == "/api/v1/knowledge/gaps":
            return httpx.Response(200, json={"unexpected": "object"})
        return httpx.Response(200, json={"ok": True})

    with pytest.raises(WorkerStageError) as caught:
        run_once(
            WorkerConfig(
                control_plane_url="https://holding.example",
                execution_kinds=(ExecutionKind.knowledge_gap_scan,),
            ),
            token_provider=lambda audience: "test-token",
            transport=httpx.MockTransport(handler),
        )

    assert caught.value.stage == WorkerStage.execute
    assert isinstance(caught.value.cause, RuntimeError)


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


def test_worker_execution_kinds_are_configurable_and_deduplicated(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_URL", "https://holding.example")
    monkeypatch.setenv(
        "WORKER_EXECUTION_KINDS",
        "knowledge_gap_scan,knowledge_outcome_review,knowledge_gap_scan",
    )

    config = WorkerConfig.from_env()
    assert config.execution_kinds == (
        ExecutionKind.knowledge_gap_scan,
        ExecutionKind.knowledge_outcome_review,
    )

    monkeypatch.setenv("WORKER_EXECUTION_KINDS", "unknown_kind")
    with pytest.raises(RuntimeError, match="unsupported execution kind"):
        WorkerConfig.from_env()

    monkeypatch.setenv("WORKER_EXECUTION_KINDS", " , ")
    with pytest.raises(RuntimeError, match="at least one"):
        WorkerConfig.from_env()


def test_worker_allows_http_only_in_explicit_local_mode(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CONTROL_PLANE_URL", "http://api:8080")
    monkeypatch.setenv("PMO_MAX_TASKS", "1")

    config = WorkerConfig.from_env()

    assert config.local_mode is True
    assert config.control_plane_url == "http://api:8080"


def test_local_worker_resolves_and_activates_canonical_agent_without_google_token(
) -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def token_provider(audience: str) -> str:
        raise AssertionError("local worker must not request a Google identity token")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        requests.append((request.method, request.url.path, body))
        assert "Authorization" not in request.headers
        assert request.headers["X-Actor"] == "local-worker:PMO_IA"

        if request.method == "GET" and request.url.path == "/api/v1/agents":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": AGENT_ID,
                        "key": "PMO_IA",
                        "name": "PMO IA",
                        "role": "Portfolio execution and dependency manager",
                        "max_autonomy": 4,
                        "model_policy": {},
                        "capabilities": [],
                        "status": "disabled",
                        "created_at": "2026-10-13T12:00:00Z",
                        "updated_at": "2026-10-13T12:00:00Z",
                    }
                ],
            )
        if request.method == "POST" and request.url.path == f"/api/v1/agents/{AGENT_ID}/transition":
            assert body == {"status": "active"}
            return httpx.Response(200, json={"ok": True})
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            assert body == {
                "agent_id": AGENT_ID,
                "execution_kinds": ["control_plane_health"],
            }
            return httpx.Response(204)
        return httpx.Response(404)

    result = run_once(
        WorkerConfig(
            control_plane_url="http://api:8080",
            local_mode=True,
        ),
        token_provider=token_provider,
        transport=httpx.MockTransport(handler),
    )

    assert result == {"processed": 0}
    assert [path for _, path, _ in requests] == [
        "/api/v1/agents",
        f"/api/v1/agents/{AGENT_ID}/transition",
        "/api/v1/pmo/claim",
    ]
