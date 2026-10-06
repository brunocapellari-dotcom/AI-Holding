from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType

import httpx

from app.pmo_worker import ControlPlaneClient, WorkerConfig, google_identity_token

GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
DEFAULT_COLLECTOR_KEY = "github-repository"
DEFAULT_FREQUENCY_SECONDS = 600
DEFAULT_FRESHNESS_SECONDS = 1800
DEFAULT_MAX_PROJECTS = 100
MAX_PROJECTS_LIMIT = 250
REQUEST_TIMEOUT_SECONDS = 20.0
TRACKED_PROJECT_STATUSES = frozenset({"active", "incubating"})
REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

TokenProvider = Callable[[str], str]


@dataclass(frozen=True)
class GitHubCollectorConfig:
    control_plane_url: str
    github_token: str
    audience: str = "holding-control-plane"
    max_projects: int = DEFAULT_MAX_PROJECTS
    collector_key: str = DEFAULT_COLLECTOR_KEY

    @classmethod
    def from_env(cls) -> GitHubCollectorConfig:
        control_plane_url = os.getenv("CONTROL_PLANE_URL", "").rstrip("/")
        if not control_plane_url.startswith("https://"):
            raise RuntimeError("CONTROL_PLANE_URL must be an https URL")

        github_token = os.getenv("GITHUB_TOKEN", "").strip()
        if not github_token:
            raise RuntimeError("GITHUB_TOKEN is required")

        try:
            max_projects = int(
                os.getenv("GITHUB_COLLECTOR_MAX_PROJECTS", str(DEFAULT_MAX_PROJECTS))
            )
        except ValueError as exc:
            raise RuntimeError("GITHUB_COLLECTOR_MAX_PROJECTS must be an integer") from exc
        if not 1 <= max_projects <= MAX_PROJECTS_LIMIT:
            raise RuntimeError(
                f"GITHUB_COLLECTOR_MAX_PROJECTS must be between 1 and {MAX_PROJECTS_LIMIT}"
            )

        return cls(
            control_plane_url=control_plane_url,
            github_token=github_token,
            audience=os.getenv("CONTROL_PLANE_AUDIENCE", "holding-control-plane"),
            max_projects=max_projects,
        )


class GitHubClient:
    def __init__(
        self,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not token.strip():
            raise RuntimeError("GitHub token cannot be blank")
        self._client = httpx.Client(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"Bearer {token.strip()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
                "User-Agent": "ai-holding-github-collector/1.0",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> GitHubClient:
        self._client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._client.__exit__(exc_type, exc_value, traceback)

    @staticmethod
    def _validate_repository(repository: str) -> str:
        normalized = repository.strip()
        if not REPOSITORY_PATTERN.fullmatch(normalized):
            raise ValueError("repository must use canonical owner/name form")
        owner, name = normalized.split("/", maxsplit=1)
        if owner in {".", ".."} or name in {".", ".."}:
            raise ValueError("repository segments cannot be dot path components")
        return normalized

    def repository_snapshot(self, repository: str) -> dict[str, object]:
        canonical = self._validate_repository(repository)

        repo_response = self._client.get(f"/repos/{canonical}")
        repo_response.raise_for_status()
        repo_body: object = repo_response.json()
        if not isinstance(repo_body, dict):
            raise RuntimeError("GitHub repository response is not an object")

        default_branch = repo_body.get("default_branch")
        actions_response = self._client.get(
            f"/repos/{canonical}/actions/runs",
            params={
                "per_page": 1,
                **(
                    {"branch": default_branch}
                    if isinstance(default_branch, str) and default_branch
                    else {}
                ),
            },
        )
        actions_response.raise_for_status()
        actions_body: object = actions_response.json()
        if not isinstance(actions_body, dict):
            raise RuntimeError("GitHub Actions response is not an object")

        workflow_runs = actions_body.get("workflow_runs")
        latest_run: dict[str, object] | None = None
        if isinstance(workflow_runs, list) and workflow_runs:
            candidate = workflow_runs[0]
            if isinstance(candidate, dict):
                latest_run = {
                    key: candidate.get(key)
                    for key in (
                        "id",
                        "name",
                        "status",
                        "conclusion",
                        "head_branch",
                        "head_sha",
                        "event",
                        "created_at",
                        "updated_at",
                        "run_attempt",
                    )
                }

        rate_remaining = actions_response.headers.get("x-ratelimit-remaining")
        return {
            "repository": canonical,
            "repo": {
                "id": repo_body.get("id"),
                "default_branch": default_branch,
                "private": repo_body.get("private"),
                "visibility": repo_body.get("visibility"),
                "archived": repo_body.get("archived"),
                "disabled": repo_body.get("disabled"),
                "pushed_at": repo_body.get("pushed_at"),
                "updated_at": repo_body.get("updated_at"),
                "open_issues_count": repo_body.get("open_issues_count"),
            },
            "latest_workflow_run": latest_run,
            "github_rate_limit_remaining": (
                int(rate_remaining)
                if isinstance(rate_remaining, str) and rate_remaining.isdigit()
                else None
            ),
        }


def _collector_definition() -> dict[str, object]:
    return {
        "key": DEFAULT_COLLECTOR_KEY,
        "source": "github-api",
        "data_type": "repository_and_ci_state",
        "frequency_seconds": DEFAULT_FREQUENCY_SECONDS,
        "freshness_sla_seconds": DEFAULT_FRESHNESS_SECONDS,
        "retry_policy": {
            "max_attempts": 3,
            "backoff": "exponential",
            "systemic_auth_failure": "fail-job",
        },
        "status": "degraded",
        "last_success_at": None,
        "last_failure_at": None,
        "last_latency_ms": None,
        "consecutive_failures": 0,
        "metadata_json": {
            "api_base": GITHUB_API_BASE,
            "api_version": GITHUB_API_VERSION,
        },
    }


def _ensure_collector(
    control_plane: ControlPlaneClient,
    project_id: str,
    collector_key: str,
) -> None:
    existing = control_plane.collectors(project_id)
    if any(item.get("key") == collector_key for item in existing):
        return
    payload = _collector_definition()
    payload["key"] = collector_key
    control_plane.upsert_collector(project_id, collector_key, payload)


def _failure_details(exc: Exception, repository: str) -> tuple[str, str, list[object]]:
    evidence: list[object] = [{"repository": repository}]
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        evidence.append({"github_status_code": status_code})
        return (
            type(exc).__name__,
            f"GitHub API returned HTTP {status_code} for {repository}",
            evidence,
        )
    return type(exc).__name__, f"GitHub collection failed for {repository}", evidence


def _cursor(snapshot: dict[str, object]) -> str | None:
    latest = snapshot.get("latest_workflow_run")
    if isinstance(latest, dict):
        head_sha = latest.get("head_sha")
        if isinstance(head_sha, str) and head_sha:
            return head_sha[:500]
        run_id = latest.get("id")
        if run_id is not None:
            return str(run_id)[:500]
    repo = snapshot.get("repo")
    if isinstance(repo, dict):
        pushed_at = repo.get("pushed_at")
        if isinstance(pushed_at, str):
            return pushed_at[:500]
    return None


def run_once(
    config: GitHubCollectorConfig,
    *,
    token_provider: TokenProvider = google_identity_token,
    control_plane_transport: httpx.BaseTransport | None = None,
    github_transport: httpx.BaseTransport | None = None,
) -> dict[str, int]:
    worker_config = WorkerConfig(
        control_plane_url=config.control_plane_url,
        audience=config.audience,
        agent_key="PMO_IA",
        max_tasks=1,
    )

    processed = 0
    succeeded = 0
    failed = 0
    skipped = 0
    snapshot_cache: dict[str, dict[str, object] | Exception] = {}

    with (
        ControlPlaneClient(
            worker_config,
            token_provider=token_provider,
            transport=control_plane_transport,
        ) as control_plane,
        GitHubClient(config.github_token, transport=github_transport) as github,
    ):
        projects = control_plane.project_registry()
        tracked = [
            item
            for item in projects
            if item.get("legacy_status") in TRACKED_PROJECT_STATUSES
            and isinstance(item.get("repository"), str)
            and str(item.get("repository", "")).strip()
        ][: config.max_projects]

        for project in tracked:
            project_id = str(project.get("project_id", "")).strip()
            project_key = str(project.get("project_key", "")).strip()
            repository = str(project.get("repository", "")).strip()
            if not project_id or not project_key or not repository:
                skipped += 1
                continue

            _ensure_collector(control_plane, project_id, config.collector_key)
            started_at = datetime.now(UTC)
            started_clock = time.monotonic()

            cached = snapshot_cache.get(repository)
            if cached is None:
                try:
                    cached = github.repository_snapshot(repository)
                except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                    cached = exc
                snapshot_cache[repository] = cached

            finished_at = datetime.now(UTC)
            latency_ms = max(0, int((time.monotonic() - started_clock) * 1000))

            if isinstance(cached, Exception):
                error_class, error_message, evidence = _failure_details(cached, repository)
                control_plane.record_collector_execution(
                    project_id,
                    config.collector_key,
                    {
                        "status": "failure",
                        "started_at": started_at.isoformat(),
                        "finished_at": finished_at.isoformat(),
                        "source_cursor": None,
                        "latency_ms": latency_ms,
                        "records_seen": 0,
                        "records_written": 0,
                        "error_class": error_class,
                        "error_message": error_message,
                        "evidence": evidence,
                        "metadata_json": {
                            "project_key": project_key,
                            "repository": repository,
                        },
                    },
                )
                failed += 1
            else:
                control_plane.record_collector_execution(
                    project_id,
                    config.collector_key,
                    {
                        "status": "success",
                        "started_at": started_at.isoformat(),
                        "finished_at": finished_at.isoformat(),
                        "source_cursor": _cursor(cached),
                        "latency_ms": latency_ms,
                        "records_seen": 2,
                        "records_written": 1,
                        "error_class": None,
                        "error_message": None,
                        "evidence": [cached],
                        "metadata_json": {
                            "project_key": project_key,
                            "repository": repository,
                        },
                    },
                )
                succeeded += 1

            control_plane.recompute_project_health(project_id)
            processed += 1

    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "unique_repositories": len(snapshot_cache),
    }


def main() -> None:
    try:
        config = GitHubCollectorConfig.from_env()
        result = run_once(config)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "event": "github_collector_failed",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    print(json.dumps(result, sort_keys=True))
    if result["failed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
