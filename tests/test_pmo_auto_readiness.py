def create_project(client, key: str):
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": f"Project {key}",
            "priority": 1,
            "autonomy_level": 4,
            "strategic_goal": "Advance explicitly autonomous work without manual readiness transitions.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_agent(client, key: str):
    response = client.post(
        "/api/v1/agents",
        json={
            "key": key,
            "name": f"Agent {key}",
            "role": "Autonomous PMO worker",
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
    execution_kind: str | None = "control_plane_health",
    auto_start: bool = False,
    depends_on: list[str] | None = None,
):
    response = client.post(
        "/api/v1/tasks",
        json={
            "key": key,
            "project_id": project_id,
            "title": f"Execute {key}",
            "priority": 0,
            "execution_kind": execution_kind,
            "auto_start": auto_start,
            "depends_on": depends_on or [],
            "idempotency_key": f"auto-{key.lower()}-0001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def claim(client, agent_id: str):
    return client.post(
        "/api/v1/pmo/claim",
        json={
            "agent_id": agent_id,
            "execution_kinds": ["control_plane_health"],
        },
    )


def transition(client, task_id: str, status: str):
    response = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        json={"status": status},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_auto_start_requires_an_explicit_execution_kind(client):
    project = create_project(client, "AUTO_KIND")
    response = client.post(
        "/api/v1/tasks",
        json={
            "key": "INVALID_AUTO",
            "project_id": project["id"],
            "title": "Invalid autonomous task",
            "auto_start": True,
            "idempotency_key": "auto-invalid-kind-0001",
        },
    )
    assert response.status_code == 422


def test_pmo_promotes_and_claims_explicit_auto_start_task(client):
    project = create_project(client, "AUTO_CLAIM")
    agent = create_agent(client, "AUTO_CLAIM_AGENT")
    task = create_task(
        client,
        project_id=project["id"],
        key="AUTO_HEALTH",
        auto_start=True,
    )
    assert task["status"] == "planned"
    assert task["auto_start"] is True

    claimed = claim(client, agent["id"])
    assert claimed.status_code == 200, claimed.text
    body = claimed.json()
    assert body["task"]["id"] == task["id"]
    assert body["task"]["status"] == "running"
    assert body["task"]["auto_start"] is True


def test_auto_start_waits_for_dependencies_then_advances(client):
    project = create_project(client, "AUTO_DEPS")
    agent = create_agent(client, "AUTO_DEPS_AGENT")
    dependency = create_task(
        client,
        project_id=project["id"],
        key="MANUAL_DEPENDENCY",
        execution_kind=None,
    )
    successor = create_task(
        client,
        project_id=project["id"],
        key="AUTO_AFTER_DEPENDENCY",
        auto_start=True,
        depends_on=[dependency["id"]],
    )

    blocked = claim(client, agent["id"])
    assert blocked.status_code == 204
    tasks = client.get("/api/v1/tasks").json()
    persisted = next(item for item in tasks if item["id"] == successor["id"])
    assert persisted["status"] == "planned"

    transition(client, dependency["id"], "ready")
    transition(client, dependency["id"], "running")
    transition(client, dependency["id"], "review")
    transition(client, dependency["id"], "done")

    claimed = claim(client, agent["id"])
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["task"]["id"] == successor["id"]


def test_planned_task_without_auto_start_is_never_implicitly_promoted(client):
    project = create_project(client, "AUTO_OPT_IN")
    agent = create_agent(client, "AUTO_OPT_IN_AGENT")
    task = create_task(
        client,
        project_id=project["id"],
        key="MANUAL_HEALTH",
        auto_start=False,
    )

    response = claim(client, agent["id"])
    assert response.status_code == 204
    tasks = client.get("/api/v1/tasks").json()
    persisted = next(item for item in tasks if item["id"] == task["id"])
    assert persisted["status"] == "planned"
