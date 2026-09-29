from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _build_execution_payload(status: str) -> dict[str, object]:
    now = datetime.now(UTC).isoformat()
    normalized = status.upper()
    return {
        "status": "success" if normalized in {"SUCCESS", "QUEUED", "WORKING", "PENDING"} else "failure",
        "started_at": now,
        "finished_at": now,
        "source_cursor": f"build-{normalized.lower()}:{normalized}",
        "latency_ms": 10,
        "records_seen": 1,
        "records_written": 1,
        "error_class": None if normalized != "FAILURE" else "CloudBuildFailure",
        "error_message": (
            None
            if normalized != "FAILURE"
            else "Cloud Build status FAILURE for Completion-Gate"
        ),
        "evidence": [
            {
                "id": f"build-{normalized.lower()}",
                "status": normalized,
                "substitutions": {
                    "REPO_NAME": "Completion-Gate",
                    "COMMIT_SHA": "abc123",
                },
            }
        ],
        "metadata_json": {
            "project_key": "COMPLETION_BUILD",
            "repository": "brunocapellari-dotcom/Completion-Gate",
        },
    }


def test_completion_gate_requires_successful_latest_holding_cloud_build(
    client: TestClient,
) -> None:
    project_response = client.post(
        "/api/v1/projects",
        json={
            "key": "COMPLETION_BUILD",
            "name": "Completion Build Project",
            "priority": 1,
            "autonomy_level": 2,
            "repository": "brunocapellari-dotcom/Completion-Gate",
            "strategic_goal": "Prove completion needs successful build evidence",
            "metadata_json": {},
        },
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    milestone = client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json={
            "key": "FINAL_GATE",
            "title": "Final gate",
            "objective": "Verify final project acceptance",
            "weight": 1,
        },
    )
    assert milestone.status_code == 201
    milestone_id = milestone.json()["id"]

    criterion = client.post(
        f"/api/v1/projects/{project_id}/milestones/{milestone_id}/criteria",
        json={
            "key": "BUILD_EVIDENCE",
            "description": "Final build evidence exists",
            "weight": 1,
        },
    )
    assert criterion.status_code == 201
    criterion_id = criterion.json()["id"]

    verified = client.post(
        (
            f"/api/v1/projects/{project_id}/milestones/{milestone_id}/criteria/"
            f"{criterion_id}/verify"
        ),
        json={"evidence": ["acceptance-test"]},
    )
    assert verified.status_code == 200

    collector = client.put(
        f"/api/v1/holding/projects/{project_id}/collectors/gcp-cloud-build",
        json={
            "key": "gcp-cloud-build",
            "source": "google-cloud-build-api",
            "data_type": "build_quality_state",
            "frequency_seconds": 300,
            "freshness_sla_seconds": 900,
            "retry_policy": {"max_attempts": 3},
            "status": "healthy",
            "last_success_at": datetime.now(UTC).isoformat(),
            "last_failure_at": None,
            "last_latency_ms": 10,
            "consecutive_failures": 0,
            "metadata_json": {},
        },
    )
    assert collector.status_code == 200

    queued = client.post(
        f"/api/v1/holding/projects/{project_id}/collectors/gcp-cloud-build/executions",
        json=_build_execution_payload("QUEUED"),
    )
    assert queued.status_code == 201

    blocked = client.get(f"/api/v1/holding/projects/{project_id}/completion-gate")
    assert blocked.status_code == 200
    blocked_body = blocked.json()
    assert blocked_body["accepted"] is False
    assert blocked_body["blocking_build_evidence"] == 1
    assert "latest Holding Cloud Build evidence is not successful" in blocked_body["reasons"]

    success = client.post(
        f"/api/v1/holding/projects/{project_id}/collectors/gcp-cloud-build/executions",
        json=_build_execution_payload("SUCCESS"),
    )
    assert success.status_code == 201

    accepted = client.get(f"/api/v1/holding/projects/{project_id}/completion-gate")
    assert accepted.status_code == 200
    accepted_body = accepted.json()
    assert accepted_body["accepted"] is True
    assert accepted_body["blocking_build_evidence"] == 0
