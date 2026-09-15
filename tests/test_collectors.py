from datetime import UTC, datetime, timedelta

from app.models.collector import Collector, CollectorStatus
from app.services.collectors import collector_is_stale


def create_agent(client):
    response = client.post(
        "/api/v1/agents",
        json={
            "key": "COLLECTOR_OWNER",
            "name": "Collector Owner",
            "role": "Own bounded internal collection",
            "max_autonomy": 3,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_collector(client, owner_agent_id: str):
    response = client.post(
        "/api/v1/collectors",
        json={
            "collector_id": "CONTROL_PLANE_STATE",
            "source": "postgresql-control-plane",
            "collector_type": "internal-state",
            "frequency_seconds": 600,
            "owner_agent_id": owner_agent_id,
            "produced_data": {"contract": "holding-state-v1"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_collector_registry_tracks_success_failure_and_recovery(client):
    owner = create_agent(client)
    collector = create_collector(client, owner["id"])
    assert collector["status"] == "disabled"
    assert collector["stale"] is False
    assert collector["failure_count"] == 0

    enabled = client.post(
        f"/api/v1/collectors/{collector['id']}/activation",
        json={"enabled": True},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["status"] == "degraded"
    assert enabled.json()["stale"] is True

    success = client.post(
        f"/api/v1/collectors/{collector['id']}/report",
        json={
            "success": True,
            "latency_ms": 42,
            "produced_data": {"projects": 10, "blocked_tasks": 2},
        },
    )
    assert success.status_code == 200, success.text
    assert success.json()["status"] == "healthy"
    assert success.json()["latency_ms"] == 42
    assert success.json()["produced_data"]["projects"] == 10
    assert success.json()["consecutive_failures"] == 0
    assert success.json()["stale"] is False

    for expected_status in ("degraded", "degraded", "failed"):
        failure = client.post(
            f"/api/v1/collectors/{collector['id']}/report",
            json={"success": False, "latency_ms": 100, "error": "source unavailable"},
        )
        assert failure.status_code == 200, failure.text
        assert failure.json()["status"] == expected_status

    assert failure.json()["failure_count"] == 3
    assert failure.json()["consecutive_failures"] == 3

    recovered = client.post(
        f"/api/v1/collectors/{collector['id']}/report",
        json={"success": True, "latency_ms": 25, "produced_data": {"projects": 10}},
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["status"] == "healthy"
    assert recovered.json()["failure_count"] == 3
    assert recovered.json()["consecutive_failures"] == 0
    assert recovered.json()["last_error"] is None


def test_disabled_collector_fails_closed_and_duplicate_id_is_rejected(client):
    owner = create_agent(client)
    collector = create_collector(client, owner["id"])

    report = client.post(
        f"/api/v1/collectors/{collector['id']}/report",
        json={"success": True, "produced_data": {}},
    )
    assert report.status_code == 409
    assert report.json()["detail"] == "disabled collector cannot report collection results"

    duplicate = client.post(
        "/api/v1/collectors",
        json={
            "collector_id": "CONTROL_PLANE_STATE",
            "source": "another-source",
            "collector_type": "internal-state",
            "frequency_seconds": 600,
        },
    )
    assert duplicate.status_code == 409


def test_failed_collection_requires_error_and_success_rejects_error(client):
    owner = create_agent(client)
    collector = create_collector(client, owner["id"])
    assert (
        client.post(
            f"/api/v1/collectors/{collector['id']}/activation",
            json={"enabled": True},
        ).status_code
        == 200
    )

    missing_error = client.post(
        f"/api/v1/collectors/{collector['id']}/report",
        json={"success": False},
    )
    assert missing_error.status_code == 422

    contradictory = client.post(
        f"/api/v1/collectors/{collector['id']}/report",
        json={"success": True, "error": "should not exist"},
    )
    assert contradictory.status_code == 422


def test_collector_staleness_is_deterministic():
    now = datetime.now(UTC)
    collector = Collector(
        collector_id="STATE",
        source="postgresql",
        collector_type="internal",
        frequency_seconds=600,
        status=CollectorStatus.healthy.value,
        last_collected_at=now - timedelta(seconds=1199),
        produced_data={},
        metadata_json={},
    )
    assert collector_is_stale(collector, now=now) is False

    collector.last_collected_at = now - timedelta(seconds=1201)
    assert collector_is_stale(collector, now=now) is True

    collector.status = CollectorStatus.disabled.value
    assert collector_is_stale(collector, now=now) is False
