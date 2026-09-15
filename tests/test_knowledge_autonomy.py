from fastapi.testclient import TestClient


def _running_execution(
    client: TestClient,
    suffix: str,
) -> tuple[dict[str, object], dict[str, object]]:
    project_response = client.post(
        "/api/v1/projects",
        json={
            "key": f"KNOW_{suffix}",
            "name": f"Knowledge Project {suffix}",
            "priority": 1,
            "autonomy_level": 4,
            "strategic_goal": "Capture reusable operational knowledge safely.",
        },
    )
    assert project_response.status_code == 201, project_response.text
    project = project_response.json()

    agent_response = client.post(
        "/api/v1/agents",
        json={
            "key": f"WORKER_{suffix}",
            "name": f"Worker {suffix}",
            "role": "Knowledge-producing execution worker",
        },
    )
    assert agent_response.status_code == 201, agent_response.text
    agent = agent_response.json()

    task_response = client.post(
        "/api/v1/tasks",
        json={
            "key": f"TASK_{suffix}",
            "project_id": project["id"],
            "title": "Produce reusable operational learning",
            "idempotency_key": f"knowledge-autonomy-{suffix.lower()}-0001",
        },
    )
    assert task_response.status_code == 201, task_response.text
    task = task_response.json()
    assert (
        client.post(f"/api/v1/tasks/{task['id']}/transition", json={"status": "ready"}).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tasks/{task['id']}/transition",
            json={"status": "running"},
        ).status_code
        == 200
    )

    run_response = client.post(
        "/api/v1/runs",
        json={"task_id": task["id"], "agent_id": agent["id"]},
    )
    assert run_response.status_code == 201, run_response.text
    run = run_response.json()
    assert (
        client.post(f"/api/v1/runs/{run['id']}/transition", json={"status": "running"}).status_code
        == 200
    )
    return agent, run


def test_successful_run_writes_reusable_learning_as_raw_claim(client: TestClient) -> None:
    agent, run = _running_execution(client, "WRITEBACK")

    succeeded = client.post(
        f"/api/v1/runs/{run['id']}/transition",
        json={
            "status": "succeeded",
            "output_metadata": {
                "artifact": "result-1",
                "knowledge": [
                    {
                        "namespace": "shared",
                        "statement": (
                            "Completed executions can contribute reusable knowledge safely."
                        ),
                        "epistemic_status": "inferred",
                        "confidence": 0.82,
                        "source_name": "execution-result",
                        "source_uri": "https://example.invalid/result-1",
                        "evidence": [
                            {
                                "source": "run-output",
                                "locator": str(run["id"]),
                            },
                            {"source": "x"},
                        ],
                    }
                ],
            },
        },
    )
    assert succeeded.status_code == 200, succeeded.text
    body = succeeded.json()
    assert body["status"] == "succeeded"
    assert body["output_metadata"]["artifact"] == "result-1"
    assert body["output_metadata"]["knowledge_capture"] == {
        "status": "captured",
        "created_claims": 1,
    }

    claims = client.get("/api/v1/knowledge/claims", params={"namespace": "shared"})
    assert claims.status_code == 200
    assert len(claims.json()) == 1
    claim = claims.json()[0]
    assert claim["lifecycle_status"] == "raw"
    assert claim["epistemic_status"] == "inferred"
    assert claim["confidence"] == 82
    assert claim["created_by_agent_id"] == agent["id"]
    assert claim["metadata_json"]["origin"] == "run_feedback"
    assert claim["metadata_json"]["run_id"] == run["id"]
    assert len(claim["evidence"]) == 1


def test_malformed_run_learning_is_skipped_without_failing_execution(client: TestClient) -> None:
    _, run = _running_execution(client, "MALFORMED")

    succeeded = client.post(
        f"/api/v1/runs/{run['id']}/transition",
        json={
            "status": "succeeded",
            "output_metadata": {
                "knowledge": [
                    {
                        "namespace": "INVALID NAMESPACE",
                        "statement": "This contribution is rejected by the knowledge schema.",
                        "source_name": "execution-result",
                    },
                    {"namespace": "shared", "statement": "x"},
                    "not-an-object",
                ]
            },
        },
    )
    assert succeeded.status_code == 200, succeeded.text
    body = succeeded.json()
    assert body["status"] == "succeeded"
    assert body["output_metadata"]["knowledge_capture"] == {
        "status": "captured",
        "created_claims": 0,
    }

    claims = client.get("/api/v1/knowledge/claims", params={"namespace": "shared"})
    assert claims.status_code == 200
    assert claims.json() == []
