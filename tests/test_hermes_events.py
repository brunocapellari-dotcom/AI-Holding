from app.core.authorization import AGENT_PERMISSIONS, AgentPermission


def event_payload() -> dict[str, object]:
    return {
        "event_id": "event-12345678",
        "event_type": "TASK_COMPLETED",
        "producer": "hermes-operational-executor",
        "project_id": "AGROLOG_MT",
        "timestamp": "2026-10-12T14:45:00Z",
        "schema_version": "1.0.0",
        "correlation_id": "correlation-12345678",
        "causation_id": "task-12345678",
        "payload": {
            "task_id": "task-12345678",
            "workflow_id": "workflow-12345678",
            "status": "COMPLETED",
        },
        "metadata": {"source": "hermes"},
    }


def test_hermes_event_ingest_is_idempotent_and_queryable(client) -> None:
    payload = event_payload()

    created = client.post("/api/v1/hermes/events", json=payload)
    replay = client.post("/api/v1/hermes/events", json=payload)
    listed = client.get("/api/v1/hermes/events")

    assert created.status_code == 201
    assert replay.status_code == 201
    assert created.json()["id"] == replay.json()["id"]
    assert created.json()["event_id"] == payload["event_id"]
    assert created.json()["project_key"] == "AGROLOG_MT"
    assert listed.status_code == 200
    assert [item["event_id"] for item in listed.json()] == [payload["event_id"]]


def test_hermes_event_id_collision_with_changed_envelope_is_rejected(client) -> None:
    payload = event_payload()
    assert client.post("/api/v1/hermes/events", json=payload).status_code == 201

    changed = event_payload()
    changed["payload"] = {"task_id": "different", "status": "FAILED"}
    response = client.post("/api/v1/hermes/events", json=changed)

    assert response.status_code == 409
    assert "different envelope" in response.json()["detail"]


def test_hermes_event_requires_timezone_aware_timestamp(client) -> None:
    payload = event_payload()
    payload["timestamp"] = "2026-10-12T14:45:00"

    response = client.post("/api/v1/hermes/events", json=payload)

    assert response.status_code == 422


def test_only_canonical_hermes_agent_receives_event_ingest_permission() -> None:
    assert AgentPermission.ingest_hermes_event in AGENT_PERMISSIONS["HERMES"]
    assert AgentPermission.ingest_hermes_event not in AGENT_PERMISSIONS["PMO_IA"]
