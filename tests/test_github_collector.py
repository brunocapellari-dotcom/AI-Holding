import json
from uuid import UUID

import httpx
import pytest

from app.github_collector import GitHubClient, GitHubCollectorConfig, run_once

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
                    "created_at": "2026-09-18T12:00:00Z",
                    "updated_at": "2026-09-18T12:00:00Z",
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
        return httpx.Response(404, json={"detail": "unexpected test request"})

    return httpx.MockTransport(handler)


def test_github_collector_caches_shared_repository_and_records_each_project() -> None:
    control_requests: list[tuple[str, str, object | None]] = []
    github_requests: list[str] = []

    def github_handler(request: httpx.Request) -> httpx.Response:
        github_requests.append(request.url.path)
        if request.url.path == "/repos/example/shared":
            return httpx.Response(
                200,
                json={
                    "id": 42,
                    "default_branch": "main",
                    "private": True,
                    "visibility": "private",
                    "archived": False,
                    "disabled": False,
                    "pushed_at": "2026-09-18T11:59:00Z",
                    "updated_at": "2026-09-18T11:59:30Z",
                    "open_issues_count": 3,
                },
            )
        if request.url.path == "/repos/example/shared/actions/runs":
            return httpx.Response(
                200,
                headers={"x-ratelimit-remaining": "4998"},
                json={
                    "workflow_runs": [
                        {
                            "id": 9001,
                            "name": "CI",
                            "status": "completed",
                            "conclusion": "success",
                            "head_branch": "main",
                            "head_sha": "abcdef123456",
                            "event": "push",
                            "created_at": "2026-09-18T11:55:00Z",
                            "updated_at": "2026-09-18T11:56:00Z",
                            "run_attempt": 1,
                        }
                    ]
                },
            )
        return httpx.Response(404)

    result = run_once(
        GitHubCollectorConfig(
            control_plane_url="https://holding.example",
            github_token="secret-token",
        ),
        token_provider=lambda audience: "google-token",
        control_plane_transport=_control_plane_transport(
            [
                _project(PROJECT_ONE, "ONE", "example/shared"),
                _project(PROJECT_TWO, "TWO", "example/shared"),
            ],
            control_requests,
        ),
        github_transport=httpx.MockTransport(github_handler),
    )

    assert result == {
        "processed": 2,
        "succeeded": 2,
        "failed": 0,
        "skipped": 0,
        "unique_repositories": 1,
    }
    assert github_requests == [
        "/repos/example/shared",
        "/repos/example/shared/actions/runs",
    ]

    executions = [
        body
        for method, path, body in control_requests
        if method == "POST" and path.endswith("/executions")
    ]
    assert len(executions) == 2
    for execution in executions:
        assert isinstance(execution, dict)
        assert execution["status"] == "success"
        assert execution["source_cursor"] == "abcdef123456"
        serialized = json.dumps(execution)
        assert "secret-token" not in serialized
        assert "google-token" not in serialized

    health_recomputes = [
        path
        for method, path, _ in control_requests
        if method == "POST" and path.endswith("/health/recompute")
    ]
    assert len(health_recomputes) == 2


def test_github_collector_records_upstream_failure_without_leaking_response_body() -> None:
    control_requests: list[tuple[str, str, object | None]] = []

    def github_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"message": "private internal repository details"},
        )

    result = run_once(
        GitHubCollectorConfig(
            control_plane_url="https://holding.example",
            github_token="secret-token",
        ),
        token_provider=lambda audience: "google-token",
        control_plane_transport=_control_plane_transport(
            [_project(PROJECT_ONE, "ONE", "example/missing")],
            control_requests,
        ),
        github_transport=httpx.MockTransport(github_handler),
    )

    assert result["processed"] == 1
    assert result["failed"] == 1
    execution = next(
        body
        for method, path, body in control_requests
        if method == "POST" and path.endswith("/executions")
    )
    assert isinstance(execution, dict)
    assert execution["status"] == "failure"
    assert execution["error_class"] == "HTTPStatusError"
    assert execution["error_message"] == "GitHub API returned HTTP 404 for example/missing"
    serialized = json.dumps(execution)
    assert "private internal repository details" not in serialized
    assert "secret-token" not in serialized


@pytest.mark.parametrize("repository", ["../repo", "owner/..", "https://github.com/a/b", "a/b/c"])
def test_github_repository_validation_blocks_noncanonical_paths(repository: str) -> None:
    with pytest.raises(ValueError):
        GitHubClient._validate_repository(repository)


def test_collector_config_requires_https_token_and_bounded_project_limit(monkeypatch) -> None:
    monkeypatch.setenv("CONTROL_PLANE_URL", "https://holding.example/")
    monkeypatch.setenv("GITHUB_TOKEN", " token ")
    monkeypatch.setenv("GITHUB_COLLECTOR_MAX_PROJECTS", "25")

    config = GitHubCollectorConfig.from_env()
    assert config.control_plane_url == "https://holding.example"
    assert config.github_token == "token"
    assert config.max_projects == 25

    monkeypatch.setenv("GITHUB_COLLECTOR_MAX_PROJECTS", "999")
    with pytest.raises(RuntimeError, match="must be between"):
        GitHubCollectorConfig.from_env()


def test_collector_skips_projects_without_repository() -> None:
    captured: list[tuple[str, str, object | None]] = []
    project = _project(str(UUID(int=5)), "NO_REPO", "example/ignored")
    project["repository"] = None

    result = run_once(
        GitHubCollectorConfig(
            control_plane_url="https://holding.example",
            github_token="secret-token",
        ),
        token_provider=lambda audience: "google-token",
        control_plane_transport=_control_plane_transport([project], captured),
        github_transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )

    assert result["processed"] == 0
    assert result["unique_repositories"] == 0
