import json

import httpx
import pytest

from app.cloud_build_collector import (
    CloudBuildClient,
    CloudBuildCollectorConfig,
    run_once,
)

PROJECT_ONE = "11111111-1111-1111-1111-111111111111"
PROJECT_TWO = "22222222-2222-2222-2222-222222222222"


def _project(project_id: str, key: str, repository: str) -> dict[str, object]:
    return {
        "project_id": project_id,
        "project_key": key,
        "name": key,
        "repository": repository,
        "legacy_status": "active",
        "operational_status": "running",
        "priority": 1,
        "autonomy_level": 2,
        "business_unit": "test",
        "mission": "test",
        "current_phase": "test",
        "knowledge_namespace": None,
        "security_level": "internal",
        "budget_micros": 0,
        "budget_currency": "BRL",
        "health": {"state": "healthy", "score": 100, "reasons": [], "signals": {}},
    }


def _control_plane_transport(
    projects: list[dict[str, object]],
    captured: list[tuple[str, str, object | None]],
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body: object | None = None
        if request.content:
            body = json.loads(request.content.decode())
        captured.append((request.method, request.url.path, body))

        if request.method == "GET" and request.url.path.endswith("/holding/projects/registry"):
            return httpx.Response(200, json=projects)
        if request.method == "GET" and request.url.path.endswith("/collectors"):
            return httpx.Response(200, json=[])
        if request.method == "PUT" and "/collectors/" in request.url.path:
            assert isinstance(body, dict)
            return httpx.Response(
                200,
                json={
                    **body,
                    "id": "33333333-3333-3333-3333-333333333333",
                    "project_id": request.url.path.split("/projects/")[1].split("/")[0],
                    "created_at": "2026-09-29T12:00:00Z",
                    "updated_at": "2026-09-29T12:00:00Z",
                },
            )
        if request.method == "POST" and request.url.path.endswith("/executions"):
            assert isinstance(body, dict)
            return httpx.Response(
                201,
                json={
                    **body,
                    "id": "44444444-4444-4444-4444-444444444444",
                    "collector_id": "33333333-3333-3333-3333-333333333333",
                },
            )
        if request.method == "POST" and request.url.path.endswith("/health/recompute"):
            return httpx.Response(
                200,
                json={"project_id": PROJECT_ONE, "state": "healthy", "score": 100},
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_cloud_build_client_selects_latest_build_and_sanitizes_failure_detail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(
            "/v1/projects/ai-holding-prod-bc/locations/southamerica-east1/builds"
        )
        return httpx.Response(
            200,
            json={
                "builds": [
                    {
                        "id": "old",
                        "status": "SUCCESS",
                        "createTime": "2026-09-29T10:00:00Z",
                        "substitutions": {"REPO_NAME": "Research-AI"},
                    },
                    {
                        "id": "new",
                        "status": "FAILURE",
                        "createTime": "2026-09-29T11:00:00Z",
                        "failureInfo": {
                            "type": "USER_BUILD_STEP",
                            "detail": "private secret-like upstream diagnostic",
                        },
                        "steps": [
                            {
                                "id": "pytest",
                                "name": "python:3.12",
                                "status": "FAILURE",
                                "exitCode": 1,
                            }
                        ],
                        "substitutions": {
                            "REPO_NAME": "Research-AI",
                            "BRANCH_NAME": "integration/final-runtime",
                            "COMMIT_SHA": "abc123",
                        },
                    },
                ]
            },
        )

    with CloudBuildClient(
        "ai-holding-prod-bc",
        "southamerica-east1",
        "access-token",
        transport=httpx.MockTransport(handler),
    ) as client:
        builds = client.latest_by_repository(100)

    snapshot = builds["research-ai"]
    assert snapshot["id"] == "new"
    assert snapshot["status"] == "FAILURE"
    assert snapshot["failure_type"] == "USER_BUILD_STEP"
    assert snapshot["steps"][0]["id"] == "pytest"
    assert snapshot["steps"][0]["exit_code"] == 1
    assert "detail" not in snapshot
    assert "private secret-like" not in json.dumps(snapshot)


def test_collector_records_build_quality_for_each_project() -> None:
    captured: list[tuple[str, str, object | None]] = []

    def cloud_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "builds": [
                    {
                        "id": "build-success",
                        "status": "SUCCESS",
                        "createTime": "2026-09-29T11:00:00Z",
                        "finishTime": "2026-09-29T11:05:00Z",
                        "substitutions": {"REPO_NAME": "Research-AI", "COMMIT_SHA": "aaa"},
                    },
                    {
                        "id": "build-failure",
                        "status": "FAILURE",
                        "createTime": "2026-09-29T11:01:00Z",
                        "finishTime": "2026-09-29T11:06:00Z",
                        "failureInfo": {"type": "USER_BUILD_STEP", "detail": "sensitive detail"},
                        "substitutions": {"REPO_NAME": "Content-Factory", "COMMIT_SHA": "bbb"},
                    },
                ]
            },
        )

    result = run_once(
        CloudBuildCollectorConfig(control_plane_url="https://holding.example"),
        access_token_provider=lambda: "access-token",
        identity_token_provider=lambda audience: "identity-token",
        control_plane_transport=_control_plane_transport(
            [
                _project(PROJECT_ONE, "RESEARCH_AI", "brunocapellari-dotcom/Research-AI"),
                _project(PROJECT_TWO, "CONTENT_FACTORY", "brunocapellari-dotcom/Content-Factory"),
            ],
            captured,
        ),
        cloud_build_transport=httpx.MockTransport(cloud_handler),
    )

    assert result["processed"] == 2
    assert result["succeeded"] == 1
    assert result["failed"] == 1
    executions = [
        body
        for method, path, body in captured
        if method == "POST" and path.endswith("/executions")
    ]
    assert len(executions) == 2
    statuses = {str(item["metadata_json"]["project_key"]): item["status"] for item in executions}
    assert statuses == {"RESEARCH_AI": "success", "CONTENT_FACTORY": "failure"}
    serialized = json.dumps(executions)
    assert "sensitive detail" not in serialized
    assert "access-token" not in serialized
    assert "identity-token" not in serialized


def test_collector_marks_missing_build_as_degraded() -> None:
    captured: list[tuple[str, str, object | None]] = []
    result = run_once(
        CloudBuildCollectorConfig(control_plane_url="https://holding.example"),
        access_token_provider=lambda: "access-token",
        identity_token_provider=lambda audience: "identity-token",
        control_plane_transport=_control_plane_transport(
            [_project(PROJECT_ONE, "ONE", "example/NoBuildRepo")],
            captured,
        ),
        cloud_build_transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"builds": []})
        ),
    )

    assert result["degraded"] == 1
    execution = next(
        body
        for method, path, body in captured
        if method == "POST" and path.endswith("/executions")
    )
    assert execution["status"] == "degraded"
    assert execution["records_seen"] == 0


def test_config_rejects_invalid_project_and_unbounded_build_limit(monkeypatch) -> None:
    monkeypatch.setenv("CONTROL_PLANE_URL", "https://holding.example")
    monkeypatch.setenv("CLOUD_BUILD_PROJECT_ID", "../project")
    with pytest.raises(RuntimeError, match="PROJECT_ID"):
        CloudBuildCollectorConfig.from_env()

    monkeypatch.setenv("CLOUD_BUILD_PROJECT_ID", "ai-holding-prod-bc")
    monkeypatch.setenv("CLOUD_BUILD_MAX_BUILDS", "9999")
    with pytest.raises(RuntimeError, match="must be between"):
        CloudBuildCollectorConfig.from_env()



def test_collector_excludes_repositories_outside_holding_gcp_scope() -> None:
    captured: list[tuple[str, str, object | None]] = []
    result = run_once(
        CloudBuildCollectorConfig(
            control_plane_url="https://holding.example",
            repositories=frozenset({"research-ai"}),
        ),
        access_token_provider=lambda: "access-token",
        identity_token_provider=lambda audience: "identity-token",
        control_plane_transport=_control_plane_transport(
            [
                _project(PROJECT_ONE, "RESEARCH_AI", "brunocapellari-dotcom/Research-AI"),
                _project(PROJECT_TWO, "AGROLOG_MT", "brunocapellari-dotcom/AgroLogMT"),
            ],
            captured,
        ),
        cloud_build_transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "builds": [
                        {
                            "id": "research-build",
                            "status": "SUCCESS",
                            "createTime": "2026-09-29T11:00:00Z",
                            "substitutions": {"REPO_NAME": "Research-AI"},
                        }
                    ]
                },
            )
        ),
    )

    assert result["processed"] == 1
    executions = [
        body
        for method, path, body in captured
        if method == "POST" and path.endswith("/executions")
    ]
    assert len(executions) == 1
    assert executions[0]["metadata_json"]["project_key"] == "RESEARCH_AI"
