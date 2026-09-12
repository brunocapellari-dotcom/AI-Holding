from app.schemas.api import ExecutionKind
from app.services.execution_policy import EXECUTION_POLICY_PROFILES


def _create_project(client, *, key: str, autonomy_level: int):
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": f"Project {key}",
            "priority": 1,
            "autonomy_level": autonomy_level,
            "strategic_goal": "Validate deterministic PMO policy enforcement.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_agent(client, *, key: str):
    response = client.post(
        "/api/v1/agents",
        json={
            "key": key,
            "name": f"Agent {key}",
            "role": "Policy-bound PMO worker",
            "max_autonomy": 4,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_ready_health_task(client, *, project_id: str, key: str):
    created = client.post(
        "/api/v1/tasks",
        json={
            "key": key,
            "project_id": project_id,
            "title": f"Execute {key}",
            "priority": 0,
            "execution_kind": "control_plane_health",
            "idempotency_key": f"policy-{key.lower()}-0001",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    ready = client.post(
        f"/api/v1/tasks/{task['id']}/transition",
        json={"status": "ready"},
    )
    assert ready.status_code == 200, ready.text
    return ready.json()


def test_every_execution_kind_has_a_code_owned_policy_profile():
    assert set(EXECUTION_POLICY_PROFILES) == set(ExecutionKind)


def test_pmo_claim_fails_closed_when_project_autonomy_is_below_policy(client):
    project = _create_project(client, key="POLICY_DENY", autonomy_level=0)
    agent = _create_agent(client, key="POLICY_DENY_AGENT")
    task = _create_ready_health_task(
        client,
        project_id=project["id"],
        key="POLICY_DENIED_HEALTH",
    )

    claimed = client.post(
        "/api/v1/pmo/claim",
        json={
            "agent_id": agent["id"],
            "execution_kinds": ["control_plane_health"],
        },
    )
    assert claimed.status_code == 204

    tasks = client.get("/api/v1/tasks").json()
    persisted = next(item for item in tasks if item["id"] == task["id"])
    assert persisted["status"] == "ready"


def test_pmo_claim_persists_policy_evidence_for_allowed_execution(client):
    project = _create_project(client, key="POLICY_ALLOW", autonomy_level=4)
    agent = _create_agent(client, key="POLICY_ALLOW_AGENT")
    task = _create_ready_health_task(
        client,
        project_id=project["id"],
        key="POLICY_ALLOWED_HEALTH",
    )

    claimed = client.post(
        "/api/v1/pmo/claim",
        json={
            "agent_id": agent["id"],
            "execution_kinds": ["control_plane_health"],
        },
    )
    assert claimed.status_code == 200, claimed.text
    body = claimed.json()
    assert body["task"]["id"] == task["id"]
    assert body["run"]["input_metadata"]["policy"] == {
        "outcome": "allow",
        "required_autonomy": 1,
        "effective_autonomy": 4,
    }
