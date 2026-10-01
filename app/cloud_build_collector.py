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

import google.auth
import httpx
from google.auth.transport.requests import Request

from app.pmo_worker import ControlPlaneClient, WorkerConfig, google_identity_token

CLOUD_BUILD_API_BASE = "https://cloudbuild.googleapis.com"
DEFAULT_PROJECT_ID = "ai-holding-prod-bc"
DEFAULT_REGION = "southamerica-east1"
DEFAULT_COLLECTOR_KEY = "gcp-cloud-build"
DEFAULT_FREQUENCY_SECONDS = 300
DEFAULT_FRESHNESS_SECONDS = 900
DEFAULT_MAX_BUILDS = 100
MAX_BUILDS_LIMIT = 500
REQUEST_TIMEOUT_SECONDS = 30.0
TRACKED_PROJECT_STATUSES = frozenset({"active", "incubating"})
TERMINAL_FAILURES = frozenset({"FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED", "EXPIRED"})
RUNNING_STATUSES = frozenset({"QUEUED", "PENDING", "WORKING"})
PROJECT_PATTERN = re.compile(r"^[a-z][a-z0-9-]{4,62}$")
REGION_PATTERN = re.compile(r"^[a-z0-9-]+$")
REPOSITORY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")

AccessTokenProvider = Callable[[], str]
IdentityTokenProvider = Callable[[str], str]


@dataclass(frozen=True)
class CloudBuildCollectorConfig:
    control_plane_url: str
    project_id: str = DEFAULT_PROJECT_ID
    region: str = DEFAULT_REGION
    audience: str = "holding-control-plane"
    max_builds: int = DEFAULT_MAX_BUILDS
    repositories: frozenset[str] = frozenset()
    collector_key: str = DEFAULT_COLLECTOR_KEY

    @classmethod
    def from_env(cls) -> CloudBuildCollectorConfig:
        control_plane_url = os.getenv("CONTROL_PLANE_URL", "").rstrip("/")
        if not control_plane_url.startswith("https://"):
            raise RuntimeError("CONTROL_PLANE_URL must be an https URL")

        project_id = os.getenv("CLOUD_BUILD_PROJECT_ID", DEFAULT_PROJECT_ID).strip()
        region = os.getenv("CLOUD_BUILD_REGION", DEFAULT_REGION).strip()
        if not PROJECT_PATTERN.fullmatch(project_id):
            raise RuntimeError("CLOUD_BUILD_PROJECT_ID is invalid")
        if not REGION_PATTERN.fullmatch(region):
            raise RuntimeError("CLOUD_BUILD_REGION is invalid")

        try:
            max_builds = int(os.getenv("CLOUD_BUILD_MAX_BUILDS", str(DEFAULT_MAX_BUILDS)))
        except ValueError as exc:
            raise RuntimeError("CLOUD_BUILD_MAX_BUILDS must be an integer") from exc
        if not 1 <= max_builds <= MAX_BUILDS_LIMIT:
            raise RuntimeError(f"CLOUD_BUILD_MAX_BUILDS must be between 1 and {MAX_BUILDS_LIMIT}")

        repositories_raw = os.getenv("CLOUD_BUILD_REPOSITORIES", "")
        repositories = frozenset(
            item.strip().casefold() for item in repositories_raw.split(",") if item.strip()
        )
        if any(not REPOSITORY_NAME_PATTERN.fullmatch(item) for item in repositories):
            raise RuntimeError("CLOUD_BUILD_REPOSITORIES contains an invalid repository name")

        return cls(
            control_plane_url=control_plane_url,
            project_id=project_id,
            region=region,
            audience=os.getenv("CONTROL_PLANE_AUDIENCE", "holding-control-plane"),
            max_builds=max_builds,
            repositories=repositories,
        )


def google_access_token() -> str:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform.read-only"]
    )
    credentials.refresh(Request())
    token = credentials.token
    if not isinstance(token, str) or not token:
        raise RuntimeError("Google access-token provider returned an invalid token")
    return token


class CloudBuildClient:
    def __init__(
        self,
        project_id: str,
        region: str,
        access_token: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not PROJECT_PATTERN.fullmatch(project_id):
            raise ValueError("invalid Google Cloud project id")
        if not REGION_PATTERN.fullmatch(region):
            raise ValueError("invalid Google Cloud region")
        if not access_token.strip():
            raise RuntimeError("Google access token cannot be blank")
        self.project_id = project_id
        self.region = region
        self._client = httpx.Client(
            base_url=CLOUD_BUILD_API_BASE,
            headers={
                "Authorization": f"Bearer {access_token.strip()}",
                "User-Agent": "ai-holding-cloud-build-collector/1.0",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> CloudBuildClient:
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
    def _repo_name(build: dict[str, object]) -> str | None:
        substitutions = build.get("substitutions")
        if isinstance(substitutions, dict):
            for key in ("REPO_NAME", "_REPO_NAME"):
                value = substitutions.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().removesuffix(".git").split("/")[-1]

        source = build.get("source")
        stack: list[object] = [source] if source is not None else []
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if (
                        key in {"repository", "repoName", "repo_name", "url", "uri"}
                        and isinstance(child, str)
                        and child.strip()
                    ):
                        candidate = child.strip().rstrip("/").removesuffix(".git")
                        if "/repositories/" in candidate:
                            candidate = candidate.rsplit("/repositories/", 1)[-1]
                        candidate = candidate.rsplit("/", 1)[-1]
                        if candidate:
                            return candidate
                    stack.append(child)
            elif isinstance(value, list):
                stack.extend(value)
        return None

    @staticmethod
    def _snapshot(build: dict[str, object], repository_name: str) -> dict[str, object]:
        substitutions = build.get("substitutions")
        selected_substitutions: dict[str, object] = {}
        if isinstance(substitutions, dict):
            for key in ("REPO_NAME", "BRANCH_NAME", "COMMIT_SHA", "REVISION_ID", "SHORT_SHA"):
                if key in substitutions:
                    selected_substitutions[key] = substitutions[key]

        failure = build.get("failureInfo")
        failure_type = failure.get("type") if isinstance(failure, dict) else None

        step_summaries: list[dict[str, object]] = []
        steps = build.get("steps")
        if isinstance(steps, list):
            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                status = step.get("status")
                exit_code = step.get("exitCode")
                step_summaries.append(
                    {
                        "index": index,
                        "id": step.get("id"),
                        "name": step.get("name"),
                        "status": status,
                        "exit_code": exit_code,
                    }
                )

        return {
            "id": build.get("id"),
            "status": build.get("status"),
            "repository_name": repository_name,
            "build_trigger_id": build.get("buildTriggerId"),
            "create_time": build.get("createTime"),
            "start_time": build.get("startTime"),
            "finish_time": build.get("finishTime"),
            "log_url": build.get("logUrl"),
            "failure_type": failure_type,
            "steps": step_summaries,
            "substitutions": selected_substitutions,
        }

    def latest_by_repository(self, max_builds: int) -> dict[str, dict[str, object]]:
        response = self._client.get(
            f"/v1/projects/{self.project_id}/locations/{self.region}/builds",
            params={"pageSize": max_builds},
        )
        response.raise_for_status()
        body: object = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("Cloud Build response is not an object")
        builds = body.get("builds", [])
        if not isinstance(builds, list):
            raise RuntimeError("Cloud Build builds response is not a list")

        candidates: list[tuple[str, str, dict[str, object]]] = []
        for item in builds:
            if not isinstance(item, dict):
                continue
            repo_name = self._repo_name(item)
            if not repo_name:
                continue
            create_time = item.get("createTime")
            sortable = create_time if isinstance(create_time, str) else ""
            candidates.append((repo_name.casefold(), sortable, item))

        latest: dict[str, dict[str, object]] = {}
        for repo_key, _, item in sorted(candidates, key=lambda row: row[1], reverse=True):
            if repo_key in latest:
                continue
            repo_name = self._repo_name(item)
            if repo_name is not None:
                latest[repo_key] = self._snapshot(item, repo_name)
        return latest


def _collector_definition(config: CloudBuildCollectorConfig) -> dict[str, object]:
    return {
        "key": config.collector_key,
        "source": "google-cloud-build-api",
        "data_type": "build_quality_state",
        "frequency_seconds": DEFAULT_FREQUENCY_SECONDS,
        "freshness_sla_seconds": DEFAULT_FRESHNESS_SECONDS,
        "retry_policy": {"max_attempts": 3, "backoff": "exponential"},
        "status": "degraded",
        "last_success_at": None,
        "last_failure_at": None,
        "last_latency_ms": None,
        "consecutive_failures": 0,
        "metadata_json": {
            "project_id": config.project_id,
            "region": config.region,
            "api_base": CLOUD_BUILD_API_BASE,
        },
    }


def _ensure_collector(
    control_plane: ControlPlaneClient,
    project_id: str,
    config: CloudBuildCollectorConfig,
) -> None:
    existing = control_plane.collectors(project_id)
    if any(item.get("key") == config.collector_key for item in existing):
        return
    control_plane.upsert_collector(
        project_id,
        config.collector_key,
        _collector_definition(config),
    )


def _execution_payload(
    snapshot: dict[str, object] | None,
    *,
    repository: str,
    project_key: str,
    started_at: datetime,
    finished_at: datetime,
    latency_ms: int,
    config: CloudBuildCollectorConfig,
) -> dict[str, object]:
    if snapshot is None:
        return {
            "status": "degraded",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "source_cursor": None,
            "latency_ms": latency_ms,
            "records_seen": 0,
            "records_written": 0,
            "error_class": None,
            "error_message": None,
            "evidence": [{"repository": repository, "build_state": "not_found"}],
            "metadata_json": {
                "project_key": project_key,
                "repository": repository,
                "gcp_project_id": config.project_id,
                "region": config.region,
            },
        }

    build_status = str(snapshot.get("status") or "UNKNOWN").upper()
    build_id = str(snapshot.get("id") or "")
    cursor = f"{build_id}:{build_status}"[:500] if build_id else build_status[:500]
    if build_status == "SUCCESS" or build_status in RUNNING_STATUSES:
        collector_status = "success"
        error_class = None
        error_message = None
    else:
        collector_status = "failure"
        error_class = "CloudBuildFailure"
        error_message = f"Cloud Build status {build_status} for {repository}"

    return {
        "status": collector_status,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "source_cursor": cursor,
        "latency_ms": latency_ms,
        "records_seen": 1,
        "records_written": 1,
        "error_class": error_class,
        "error_message": error_message,
        "evidence": [snapshot],
        "metadata_json": {
            "project_key": project_key,
            "repository": repository,
            "gcp_project_id": config.project_id,
            "region": config.region,
            "evidence_uri": (
                f"gs://{config.project_id}-ai-execution-evidence/"
                f"{repository.rsplit('/', 1)[-1]}/{build_id}/"
                if build_id
                else None
            ),
        },
    }


def run_once(
    config: CloudBuildCollectorConfig,
    *,
    access_token_provider: AccessTokenProvider = google_access_token,
    identity_token_provider: IdentityTokenProvider = google_identity_token,
    control_plane_transport: httpx.BaseTransport | None = None,
    cloud_build_transport: httpx.BaseTransport | None = None,
) -> dict[str, int]:
    worker_config = WorkerConfig(
        control_plane_url=config.control_plane_url,
        audience=config.audience,
        agent_key="PMO_IA",
        max_tasks=1,
    )
    access_token = access_token_provider()

    processed = 0
    succeeded = 0
    failed = 0
    degraded = 0
    skipped = 0

    with (
        ControlPlaneClient(
            worker_config,
            token_provider=identity_token_provider,
            transport=control_plane_transport,
        ) as control_plane,
        CloudBuildClient(
            config.project_id,
            config.region,
            access_token,
            transport=cloud_build_transport,
        ) as cloud_build,
    ):
        builds = cloud_build.latest_by_repository(config.max_builds)
        projects = control_plane.project_registry()
        tracked = [
            item
            for item in projects
            if item.get("legacy_status") in TRACKED_PROJECT_STATUSES
            and isinstance(item.get("repository"), str)
            and str(item.get("repository", "")).strip()
            and (
                not config.repositories
                or str(item.get("repository", "")).rsplit("/", 1)[-1].casefold()
                in config.repositories
            )
        ]

        for project in tracked:
            project_id = str(project.get("project_id", "")).strip()
            project_key = str(project.get("project_key", "")).strip()
            repository = str(project.get("repository", "")).strip()
            if not project_id or not project_key or not repository:
                skipped += 1
                continue

            _ensure_collector(control_plane, project_id, config)
            started_at = datetime.now(UTC)
            started_clock = time.monotonic()
            repository_name = repository.rsplit("/", 1)[-1]
            snapshot = builds.get(repository_name.casefold())
            finished_at = datetime.now(UTC)
            latency_ms = max(0, int((time.monotonic() - started_clock) * 1000))
            payload = _execution_payload(
                snapshot,
                repository=repository,
                project_key=project_key,
                started_at=started_at,
                finished_at=finished_at,
                latency_ms=latency_ms,
                config=config,
            )
            control_plane.record_collector_execution(
                project_id,
                config.collector_key,
                payload,
            )
            control_plane.recompute_project_health(project_id)
            processed += 1

            status = payload["status"]
            if status == "success":
                succeeded += 1
            elif status == "failure":
                failed += 1
            else:
                degraded += 1

    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "degraded": degraded,
        "skipped": skipped,
        "builds_seen": len(builds),
    }


def main() -> None:
    try:
        result = run_once(CloudBuildCollectorConfig.from_env())
    except Exception as exc:
        print(
            json.dumps(
                {
                    "event": "cloud_build_collector_failed",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
