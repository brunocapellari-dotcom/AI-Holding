from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _create_project(client: TestClient, key: str, repository: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": f"{key} Project",
            "priority": 1,
            "autonomy_level": 2,
            "repository": repository,
            "strategic_goal": "Validate execution fabric state",
            "metadata_json": {},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_execution_fabric_reports_latest_cloud_build_evidence(client: TestClient) -> None:
    project = _create_project(
        client,
        "EXEC_FABRIC",
        "brunocapellari-dotcom/Research-AI",
    )
    project_id = project["id"]

    collector = client.put(
        f"/api/v1/holding/projects/{project_id}/collectors/gcp-cloud-build",
        json={
            "key": "gcp-cloud-build",
            "source": "google-cloud-build-api",
            "data_type": "build_quality_state",
            "frequency_seconds": 300,
            "freshness_sla_seconds": 900,
            "retry_policy": {"max_attempts": 3},
            "status": "degraded",
            "last_success_at": None,
            "last_failure_at": None,
            "last_latency_ms": None,
            "consecutive_failures": 0,
            "metadata_json": {
                "project_id": "ai-holding-prod-bc",
                "region": "southamerica-east1",
            },
        },
    )
    assert collector.status_code == 200

    now = datetime.now(UTC).isoformat()
    execution = client.post(
        f"/api/v1/holding/projects/{project_id}/collectors/gcp-cloud-build/executions",
        json={
            "status": "success",
            "started_at": now,
            "finished_at": now,
            "source_cursor": "build-123:SUCCESS",
            "latency_ms": 20,
            "records_seen": 1,
            "records_written": 1,
            "error_class": None,
            "error_message": None,
            "evidence": [
                {
                    "id": "build-123",
                    "status": "SUCCESS",
                    "log_url": "https://console.cloud.google.com/cloud-build/builds/build-123",
                    "failure_type": None,
                    "steps": [
                        {
                            "id": "full-project-gate",
                            "name": "python:3.12",
                            "status": "SUCCESS",
                            "exit_code": 0,
                        }
                    ],
                    "substitutions": {
                        "REPO_NAME": "Research-AI",
                        "BRANCH_NAME": "integration/final-runtime",
                        "COMMIT_SHA": "abc123",
                    },
                }
            ],
            "metadata_json": {
                "project_key": "EXEC_FABRIC",
                "repository": "brunocapellari-dotcom/Research-AI",
                "gcp_project_id": "ai-holding-prod-bc",
                "region": "southamerica-east1",
                "evidence_uri": (
                    "gs://ai-holding-prod-bc-ai-execution-evidence/"
                    "Research-AI/build-123/"
                ),
            },
        },
    )
    assert execution.status_code == 201

    response = client.get("/api/v1/holding/execution-fabric")
    assert response.status_code == 200
    body = response.json()
    row = next(item for item in body["projects"] if item["project_key"] == "EXEC_FABRIC")
    assert row["cloud_build_state"] == "success"
    assert row["build_id"] == "build-123"
    assert row["branch"] == "integration/final-runtime"
    assert row["commit_sha"] == "abc123"
    assert row["evidence_uri"].endswith("/Research-AI/build-123/")
    assert row["failed_step_id"] is None
    assert body["totals"]["success"] >= 1



def test_execution_fabric_reports_failed_step_without_log_content(
    client: TestClient,
) -> None:
    project = _create_project(
        client,
        "EXEC_FAILURE",
        "brunocapellari-dotcom/Content-Factory",
    )
    project_id = project["id"]
    client.put(
        f"/api/v1/holding/projects/{project_id}/collectors/gcp-cloud-build",
        json={
            "key": "gcp-cloud-build",
            "source": "google-cloud-build-api",
            "data_type": "build_quality_state",
            "frequency_seconds": 300,
            "freshness_sla_seconds": 900,
            "retry_policy": {"max_attempts": 3},
            "status": "degraded",
            "last_success_at": None,
            "last_failure_at": None,
            "last_latency_ms": None,
            "consecutive_failures": 0,
            "metadata_json": {},
        },
    )
    now = datetime.now(UTC).isoformat()
    response = client.post(
        f"/api/v1/holding/projects/{project_id}/collectors/gcp-cloud-build/executions",
        json={
            "status": "failure",
            "started_at": now,
            "finished_at": now,
            "source_cursor": "build-failed:FAILURE",
            "latency_ms": 15,
            "records_seen": 1,
            "records_written": 1,
            "error_class": "CloudBuildFailure",
            "error_message": "Cloud Build status FAILURE for Content-Factory",
            "evidence": [
                {
                    "id": "build-failed",
                    "status": "FAILURE",
                    "failure_type": "USER_BUILD_STEP",
                    "steps": [
                        {
                            "id": "quality-and-e2e",
                            "name": "python:3.12",
                            "status": "FAILURE",
                            "exit_code": 2,
                        }
                    ],
                    "substitutions": {
                        "REPO_NAME": "Content-Factory",
                        "COMMIT_SHA": "deadbeef",
                    },
                }
            ],
            "metadata_json": {
                "project_key": "EXEC_FAILURE",
                "repository": "brunocapellari-dotcom/Content-Factory",
            },
        },
    )
    assert response.status_code == 201

    collector = client.get(
        f"/api/v1/holding/projects/{project_id}/collectors"
    ).json()[0]
    assert collector["status"] == "failing"

    fabric = client.get("/api/v1/holding/execution-fabric").json()
    row = next(item for item in fabric["projects"] if item["project_key"] == "EXEC_FAILURE")
    assert row["cloud_build_state"] == "failure"
    assert row["failure_type"] == "USER_BUILD_STEP"
    assert row["failed_step_id"] == "quality-and-e2e"
    assert row["failed_step_exit_code"] == 2
    assert row["failure_category"] == "project-quality"
    assert row["remediation_owner"] == "project"
    assert row["retry_safe"] is False
    assert "Fix the failing project test" in row["recommended_action"]
