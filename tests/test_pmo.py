from uuid import uuid4

EXECUTION_KINDS = ["control_plane_health"]


def create_project(client, key: str, priority: int = 1):
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": f"Project {key}",
            "priority": priority,
            "autonomy_level": 4,
            "strategic_goal": "Execute deterministic autonomous work with evidence.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_agent(client, key: str = "PMO_WORKER"):
    response = client.post(
        "/api/v1/agents",
        json={
            "key": key,
            "name": f"Worker {key}",
            "role": "Autonomous execution worker",
            "max_autonomy": 4,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_task(
    client,
    *,
    project_id: str,
    key: str,
    priority: int,
    depends_on: list[str] | None = None,
    assigned_agent_id: str | None = None,
    execution_kind: str | None = "control_plane_health",
):
    response = client.post(
        "/api/v1/tasks",
        json={
            "key": key,
            "project_id": project_id,
            "title": f"Execute {key}",
            "priority": priority,
            "assigned_agent_id": assigned_agent_id,
            "execution_kind": execution_kind,
            "depends_on": depends_on or [],
            "evidence_required": False,
            "idempotency_key": f"pmo-{key.lower()}-0001",
        },
    )
    assert response.status_code == 201, response.text
    task = response.json()
    ready = client.post(
        f"/api/v1/tasks/{task['id']}/transition",
        json={"status": "ready"},
    )
    assert ready.status_code == 200, ready.text
    return ready.json()


def claim_payload(agent_id: str, project_id: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "agent_id": agent_id,
        "execution_kinds": EXECUTION_KINDS,
    }
    if project_id is not None:
        payload["project_id"] = project_id
    return payload


def test_pmo_claim_selects_highest_priority_eligible_task_and_creates_run(client):
    project = create_project(client, "PMO_CLAIM")
    agent = create_agent(client)
    low = create_task(
        client,
        project_id=project["id"],
        key="LOW_PRIORITY",
        priority=4,
    )
    high = create_task(
        client,
        project_id=project["id"],
        key="HIGH_PRIORITY",
        priority=0,
    )

    claimed = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"]),
    )
    assert claimed.status_code == 200, claimed.text
    body = claimed.json()
    assert body["task"]["id"] == high["id"]
    assert body["task"]["execution_kind"] == "control_plane_health"
    assert body["task"]["status"] == "running"
    assert body["task"]["assigned_agent_id"] == agent["id"]
    assert body["run"]["task_id"] == high["id"]
    assert body["run"]["agent_id"] == agent["id"]
    assert body["run"]["status"] == "queued"
    assert body["run"]["attempt"] == 1
    assert body["run"]["input_metadata"]["execution_kind"] == "control_plane_health"

    second = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"]),
    )
    assert second.status_code == 200
    assert second.json()["task"]["id"] == low["id"]

    none_left = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"]),
    )
    assert none_left.status_code == 204


def test_pmo_claim_does_not_pick_untyped_arbitrary_work(client):
    project = create_project(client, "PMO_BOUNDED")
    agent = create_agent(client, "BOUNDED_WORKER")
    create_task(
        client,
        project_id=project["id"],
        key="UNTYPED_TASK",
        priority=0,
        execution_kind=None,
    )

    response = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"]),
    )
    assert response.status_code == 204


def test_pmo_claim_respects_dependencies_and_project_filter(client):
    project_a = create_project(client, "PMO_A")
    project_b = create_project(client, "PMO_B")
    agent = create_agent(client, "FILTER_WORKER")

    dependency = create_task(
        client,
        project_id=project_a["id"],
        key="DEPENDENCY",
        priority=1,
    )
    blocked_by_dependency = create_task(
        client,
        project_id=project_a["id"],
        key="AFTER_DEPENDENCY",
        priority=0,
        depends_on=[dependency["id"]],
    )
    project_b_task = create_task(
        client,
        project_id=project_b["id"],
        key="PROJECT_B_TASK",
        priority=0,
    )

    claim_a = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"], project_a["id"]),
    )
    assert claim_a.status_code == 200
    assert claim_a.json()["task"]["id"] == dependency["id"]

    still_blocked = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"], project_a["id"]),
    )
    assert still_blocked.status_code == 204

    assert (
        client.post(
            f"/api/v1/runs/{claim_a.json()['run']['id']}/transition",
            json={"status": "running"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/runs/{claim_a.json()['run']['id']}/transition",
            json={"status": "succeeded"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tasks/{dependency['id']}/transition",
            json={"status": "review"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/tasks/{dependency['id']}/transition",
            json={"status": "done"},
        ).status_code
        == 200
    )

    unblocked = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"], project_a["id"]),
    )
    assert unblocked.status_code == 200
    assert unblocked.json()["task"]["id"] == blocked_by_dependency["id"]

    claim_b = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(agent["id"], project_b["id"]),
    )
    assert claim_b.status_code == 200
    assert claim_b.json()["task"]["id"] == project_b_task["id"]


def test_pmo_claim_rejects_missing_or_inactive_agent_and_foreign_assignment(client):
    project = create_project(client, "PMO_AGENT")
    active_agent = create_agent(client, "ACTIVE_WORKER")
    other_agent = create_agent(client, "OTHER_WORKER")
    create_task(
        client,
        project_id=project["id"],
        key="ASSIGNED_OTHER",
        priority=0,
        assigned_agent_id=other_agent["id"],
    )

    missing = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(str(uuid4())),
    )
    assert missing.status_code == 404

    assert (
        client.post(
            f"/api/v1/agents/{active_agent['id']}/transition",
            json={"status": "disabled"},
        ).status_code
        == 200
    )
    inactive = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(active_agent["id"]),
    )
    assert inactive.status_code == 409

    no_foreign_claim = client.post(
        "/api/v1/pmo/claim",
        json=claim_payload(other_agent["id"], project["id"]),
    )
    assert no_foreign_claim.status_code == 200
    assert no_foreign_claim.json()["task"]["assigned_agent_id"] == other_agent["id"]
