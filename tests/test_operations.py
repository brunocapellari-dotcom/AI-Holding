from uuid import uuid4


def create_project(client, key: str = "OPS"):
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": f"Operations {key}",
            "priority": 1,
            "autonomy_level": 4,
            "strategic_goal": "Operate the holding reliably with deterministic controls.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_running_task(client, project_id: str, key: str = "RUN_TASK"):
    response = client.post(
        "/api/v1/tasks",
        json={
            "key": key,
            "project_id": project_id,
            "title": "Execute deterministic operation",
            "idempotency_key": f"ops-{key.lower()}-0001",
        },
    )
    assert response.status_code == 201, response.text
    task = response.json()
    assert client.post(
        f"/api/v1/tasks/{task['id']}/transition", json={"status": "ready"}
    ).status_code == 200
    assert client.post(
        f"/api/v1/tasks/{task['id']}/transition", json={"status": "running"}
    ).status_code == 200
    return task


def test_agent_registry_lifecycle_and_duplicate_capabilities(client):
    created = client.post(
        "/api/v1/agents",
        json={
            "key": "PMO_IA",
            "name": "PMO IA",
            "role": "Portfolio execution manager",
            "max_autonomy": 4,
            "model_policy": {"default": "llama"},
            "capabilities": ["task-routing", "task-routing", "dependency-management"],
        },
    )
    assert created.status_code == 201, created.text
    agent = created.json()
    assert agent["capabilities"] == ["task-routing", "dependency-management"]

    duplicate = client.post(
        "/api/v1/agents",
        json={
            "key": "PMO_IA",
            "name": "Duplicate PMO",
            "role": "Duplicate",
        },
    )
    assert duplicate.status_code == 409

    degraded = client.post(
        f"/api/v1/agents/{agent['id']}/transition",
        json={"status": "degraded"},
    )
    assert degraded.status_code == 200
    disabled = client.post(
        f"/api/v1/agents/{agent['id']}/transition",
        json={"status": "disabled"},
    )
    assert disabled.status_code == 200
    invalid = client.post(
        f"/api/v1/agents/{agent['id']}/transition",
        json={"status": "degraded"},
    )
    assert invalid.status_code == 409
    restored = client.post(
        f"/api/v1/agents/{agent['id']}/transition",
        json={"status": "active"},
    )
    assert restored.status_code == 200
    assert len(client.get("/api/v1/agents").json()) == 1
    missing_agent = client.post(
        f"/api/v1/agents/{uuid4()}/transition", json={"status": "active"}
    )
    assert missing_agent.status_code == 404


def test_run_lifecycle_is_idempotent_and_blocks_parallel_execution(client):
    project = create_project(client)
    task = create_running_task(client, project["id"])
    agent = client.post(
        "/api/v1/agents",
        json={"key": "WORKER", "name": "Worker", "role": "Execution worker"},
    ).json()

    created = client.post(
        "/api/v1/runs",
        json={
            "task_id": task["id"],
            "agent_id": agent["id"],
            "external_run_id": "worker-run-001",
            "input_metadata": {"source": "scheduler"},
        },
    )
    assert created.status_code == 201, created.text
    run = created.json()
    assert run["attempt"] == 1
    assert run["status"] == "queued"

    replay = client.post(
        "/api/v1/runs",
        json={
            "task_id": task["id"],
            "agent_id": agent["id"],
            "external_run_id": "worker-run-001",
        },
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == run["id"]

    parallel = client.post("/api/v1/runs", json={"task_id": task["id"]})
    assert parallel.status_code == 409

    started = client.post(
        f"/api/v1/runs/{run['id']}/transition", json={"status": "running"}
    )
    assert started.status_code == 200
    assert started.json()["started_at"] is not None
    succeeded = client.post(
        f"/api/v1/runs/{run['id']}/transition",
        json={"status": "succeeded", "output_metadata": {"artifact": "result-1"}},
    )
    assert succeeded.status_code == 200
    assert succeeded.json()["finished_at"] is not None
    assert succeeded.json()["output_metadata"] == {"artifact": "result-1"}
    assert client.post(
        f"/api/v1/runs/{run['id']}/transition", json={"status": "running"}
    ).status_code == 409

    retry = client.post(
        "/api/v1/runs",
        json={"task_id": task["id"], "agent_id": agent["id"]},
    )
    assert retry.status_code == 201
    assert retry.json()["attempt"] == 2
    assert len(client.get(f"/api/v1/runs?task_id={task['id']}").json()) == 2


def test_run_validation_rejects_bad_task_agent_and_failure_payload(client):
    project = create_project(client, "VALIDATE")
    pending_task = client.post(
        "/api/v1/tasks",
        json={
            "key": "PENDING_TASK",
            "project_id": project["id"],
            "title": "Pending task",
            "idempotency_key": "pending-task-0001",
        },
    ).json()
    assert client.post("/api/v1/runs", json={"task_id": pending_task["id"]}).status_code == 409
    assert client.post("/api/v1/runs", json={"task_id": str(uuid4())}).status_code == 404

    task = create_running_task(client, project["id"], "SECOND_TASK")
    agent = client.post(
        "/api/v1/agents",
        json={"key": "OFFLINE", "name": "Offline", "role": "Worker"},
    ).json()
    assert client.post(
        f"/api/v1/agents/{agent['id']}/transition", json={"status": "disabled"}
    ).status_code == 200
    assert client.post(
        "/api/v1/runs", json={"task_id": task["id"], "agent_id": agent["id"]}
    ).status_code == 409
    assert client.post(
        "/api/v1/runs", json={"task_id": task["id"], "agent_id": str(uuid4())}
    ).status_code == 400

    run = client.post("/api/v1/runs", json={"task_id": task["id"]}).json()
    assert client.post(
        f"/api/v1/runs/{run['id']}/transition", json={"status": "failed"}
    ).status_code == 422
    assert client.post(
        f"/api/v1/runs/{run['id']}/transition",
        json={"status": "running", "error": "not valid here"},
    ).status_code == 422
    missing_run = client.post(
        f"/api/v1/runs/{uuid4()}/transition", json={"status": "running"}
    )
    assert missing_run.status_code == 404


def test_incident_lifecycle_requires_resolution_evidence(client):
    project = create_project(client, "INCIDENT")
    created = client.post(
        "/api/v1/incidents",
        json={
            "project_id": project["id"],
            "severity": "sev2",
            "title": "Source freshness failure",
            "source": "source-health",
            "details": {"source": "telemetry"},
        },
    )
    assert created.status_code == 201, created.text
    incident = created.json()
    assert incident["status"] == "open"

    investigating = client.post(
        f"/api/v1/incidents/{incident['id']}/transition",
        json={"status": "investigating", "root_cause": "Upstream feed delayed"},
    )
    assert investigating.status_code == 200
    assert investigating.json()["root_cause"] == "Upstream feed delayed"

    no_evidence = client.post(
        f"/api/v1/incidents/{incident['id']}/transition", json={"status": "resolved"}
    )
    assert no_evidence.status_code == 422
    resolved = client.post(
        f"/api/v1/incidents/{incident['id']}/transition",
        json={"status": "resolved", "resolution": {"evidence": "freshness-check-42"}},
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolved_at"] is not None
    assert client.post(
        f"/api/v1/incidents/{incident['id']}/transition", json={"status": "investigating"}
    ).status_code == 409
    assert len(client.get("/api/v1/incidents?incident_status=resolved").json()) == 1

    assert client.post(
        "/api/v1/incidents",
        json={
            "project_id": str(uuid4()),
            "severity": "sev3",
            "title": "Missing project",
            "source": "test",
        },
    ).status_code == 400
    assert client.post(
        f"/api/v1/incidents/{uuid4()}/transition", json={"status": "investigating"}
    ).status_code == 404
