from __future__ import annotations


def _event(event_id: str, project_key: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": "TASK_COMPLETED",
        "producer": "hermes-operational-worker",
        "project_id": project_key,
        "timestamp": "2026-10-13T12:00:00Z",
        "schema_version": "1.0.0",
        "correlation_id": "correlation-12345678",
        "payload": {"secret": "do-not-render-or-return"},
        "metadata": {"access_token": "do-not-render-or-return"},
    }


def test_operational_feed_reports_only_persisted_sanitized_events(client) -> None:
    assert (
        client.post(
            "/api/v1/hermes/events", json=_event("event-00000001", "AGROLOG_MT")
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/hermes/events", json=_event("event-00000002", "RESEARCH_AI")
        ).status_code
        == 201
    )

    response = client.get("/api/v1/holding/control-plane/event-feed?project_key=AGROLOG_MT")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["kind"] == "recorded_hermes_activity"
    assert body["availability_verified"] is False
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["event_id"] == "event-00000001"
    assert item["project_key"] == "AGROLOG_MT"
    assert "received_at" in item
    assert item["received_age_seconds"] >= 0
    assert "payload" not in item
    assert "metadata" not in item
    assert "secret" not in response.text
    assert "access_token" not in response.text


def test_operational_feed_limits_and_empty_filter(client) -> None:
    assert client.get("/api/v1/holding/control-plane/event-feed?limit=101").status_code == 422
    assert client.get("/api/v1/holding/control-plane/event-feed?limit=0").status_code == 422
    response = client.get("/api/v1/holding/control-plane/event-feed?project_key=UNKNOWN")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_owner_console_displays_live_hermes_event_panel(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "/api/v1/holding/control-plane/event-feed" in response.text
    assert "Atividade recebida do Hermes" in response.text
    assert "Não comprovam" not in response.text
