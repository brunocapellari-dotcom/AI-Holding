import json

import httpx
import pytest

from app.pmo_worker import WorkerConfig, run_once

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

        if request.method == "GET" and request.url.path == "/api/v1/agents":
            return httpx.Response(200, json=[{"id": AGENT_ID, "key": "PMO_IA"}])
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            assert body == {
                "agent_id": AGENT_ID,
                "execution_kinds": ["control_plane_health"],
            }
            claim_count += 1
            if claim_count == 1:
                return httpx.Response(200, json=claim_payload())
            return httpx.Response(204)
        if request.method == "GET" and request.url.path == "/healthz":
            return httpx.Response(200, json={"status": "ok"})
        if request.method == "GET" and request.url.path == "/readyz":
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
    run_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/runs/{RUN_ID}/transition"
    ]
    assert run_transitions[0] == {"status": "running", "output_metadata": {}}
    assert run_transitions[1]["status"] == "succeeded"
    output = run_transitions[1]["output_metadata"]
    assert output["execution_kind"] == "control_plane_health"
    assert output["evidence"]["/healthz"]["status_code"] == 200
    assert output["evidence"]["/readyz"]["status_code"] == 200

    task_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/tasks/{TASK_ID}/transition"
    ]
    assert task_transitions == [{"status": "review"}]


def test_worker_failure_marks_run_and_task_and_creates_incident():
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        requests.append((request.method, request.url.path, body))
        if request.method == "GET" and request.url.path == "/api/v1/agents":
            return httpx.Response(200, json=[{"id": AGENT_ID, "key": "PMO_IA"}])
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            return httpx.Response(200, json=claim_payload())
        if request.method == "GET" and request.url.path == "/healthz":
            return httpx.Response(200, json={"status": "ok"})
        if request.method == "GET" and request.url.path == "/readyz":
            return httpx.Response(503, json={"status": "not-ready"})
        return httpx.Response(200, json={"ok": True})

    with pytest.raises(httpx.HTTPStatusError):
        run_once(
            WorkerConfig(control_plane_url="https://holding.example"),
            token_provider=lambda audience: "test-token",
            transport=httpx.MockTransport(handler),
        )

    run_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/runs/{RUN_ID}/transition"
    ]
    assert [item["status"] for item in run_transitions] == ["running", "failed"]
    assert "503 Service Unavailable" in run_transitions[1]["error"]

    task_transitions = [
        body
        for method, path, body in requests
        if method == "POST" and path == f"/api/v1/tasks/{TASK_ID}/transition"
    ]
    assert task_transitions[0]["status"] == "blocked"
    assert "503 Service Unavailable" in task_transitions[0]["blocked_reason"]

    incidents = [
        body
        for method, path, body in requests
        if method == "POST" and path == "/api/v1/incidents"
    ]
    assert len(incidents) == 1
    assert incidents[0]["project_id"] == PROJECT_ID
    assert incidents[0]["severity"] == "sev3"
    assert incidents[0]["details"]["task_id"] == TASK_ID


def test_worker_configuration_fails_closed(monkeypatch):
    monkeypatch.delenv("CONTROL_PLANE_URL", raising=False)
    with pytest.raises(RuntimeError, match="https URL"):
        WorkerConfig.from_env()

    monkeypatch.setenv("CONTROL_PLANE_URL", "https://holding.example")
    monkeypatch.setenv("PMO_MAX_TASKS", "11")
    with pytest.raises(RuntimeError, match="between 1 and 10"):
        WorkerConfig.from_env()
