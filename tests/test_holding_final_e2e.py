from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def _project(client: TestClient, key: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": key,
            "priority": 1,
            "autonomy_level": 4,
            "strategic_goal": "Exercise the final Holding acceptance gate",
            "metadata_json": {},
        },
    )
    assert response.status_code == 201
    return response.json()


def _profile_payload(status: str, budget_micros: int = 0) -> dict[str, object]:
    return {
        "mission": "Final Holding E2E",
        "operational_status": status,
        "knowledge_namespace": "holding-e2e",
        "current_phase": "acceptance",
        "security_level": "restricted",
        "budget_micros": budget_micros,
        "budget_currency": "BRL",
        "metadata_json": {},
    }


def test_completed_is_rejected_without_evidence_and_accepted_after_verification(
    client: TestClient,
) -> None:
    project = _project(client, "E2E_COMPLETION")
    project_id = project["id"]

    rejected = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json=_profile_payload("completed"),
    )
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["gate"]["accepted"] is False

    milestone = client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json={
            "key": "FINAL",
            "title": "Final acceptance",
            "objective": "Prove the project acceptance criteria",
            "weight": 100,
        },
    )
    assert milestone.status_code == 201
    milestone_id = milestone.json()["id"]

    criterion = client.post(
        f"/api/v1/projects/{project_id}/milestones/{milestone_id}/criteria",
        json={
            "key": "FULL_GATE",
            "description": "The complete acceptance gate has objective evidence",
            "weight": 100,
        },
    )
    assert criterion.status_code == 201
    criterion_id = criterion.json()["id"]

    verified = client.post(
        f"/api/v1/projects/{project_id}/milestones/{milestone_id}/criteria/{criterion_id}/verify",
        json={"evidence": ["full-project-gate-evidence"]},
    )
    assert verified.status_code == 200

    gate = client.get(f"/api/v1/holding/projects/{project_id}/completion-gate")
    assert gate.status_code == 200
    assert gate.json()["accepted"] is True

    completed = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json=_profile_payload("completed"),
    )
    assert completed.status_code == 200
    assert completed.json()["operational_status"] == "completed"


def test_collector_failure_opens_alert_and_success_recovers_it(client: TestClient) -> None:
    project = _project(client, "E2E_COLLECTOR")
    project_id = project["id"]
    now = datetime.now(UTC)

    profile = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json=_profile_payload("running"),
    )
    assert profile.status_code == 200

    collector = client.put(
        f"/api/v1/holding/projects/{project_id}/collectors/github",
        json={
            "key": "github",
            "source": "github",
            "data_type": "repository_state",
            "frequency_seconds": 60,
            "freshness_sla_seconds": 600,
            "retry_policy": {"max_attempts": 3},
            "status": "healthy",
            "last_success_at": now.isoformat(),
            "consecutive_failures": 0,
            "metadata_json": {},
        },
    )
    assert collector.status_code == 200

    for attempt in range(3):
        started = now + timedelta(seconds=attempt * 2)
        failed = client.post(
            f"/api/v1/holding/projects/{project_id}/collectors/github/executions",
            json={
                "status": "failure",
                "started_at": started.isoformat(),
                "finished_at": (started + timedelta(seconds=1)).isoformat(),
                "latency_ms": 100,
                "records_seen": 0,
                "records_written": 0,
                "error_class": "UpstreamError",
                "error_message": "synthetic outage",
                "evidence": [{"attempt": attempt + 1}],
                "metadata_json": {},
            },
        )
        assert failed.status_code == 201

    degraded = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
    assert degraded.status_code == 200
    assert degraded.json()["state"] in {"degraded", "at_risk"}

    contract = client.get(f"/api/v1/holding/projects/{project_id}/contract")
    assert contract.status_code == 200
    alerts = contract.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["source"] == "collector-health"
    assert alerts[0]["status"] == "active"

    recovered_start = now + timedelta(minutes=1)
    recovered = client.post(
        f"/api/v1/holding/projects/{project_id}/collectors/github/executions",
        json={
            "status": "success",
            "started_at": recovered_start.isoformat(),
            "finished_at": (recovered_start + timedelta(seconds=1)).isoformat(),
            "latency_ms": 75,
            "records_seen": 5,
            "records_written": 5,
            "evidence": ["recovered"],
            "metadata_json": {},
        },
    )
    assert recovered.status_code == 201

    healthy = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
    assert healthy.status_code == 200
    assert healthy.json()["state"] == "healthy"
    contract = client.get(f"/api/v1/holding/projects/{project_id}/contract")
    assert contract.json()["alerts"] == []


def test_finops_anomaly_opens_investigation_and_blocks_completion(client: TestClient) -> None:
    project = _project(client, "E2E_FINOPS")
    project_id = project["id"]
    now = datetime.now(UTC)

    profile = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json=_profile_payload("running", budget_micros=10_000_000_000),
    )
    assert profile.status_code == 200

    for days_ago in range(2, 9):
        baseline = client.post(
            "/api/v1/holding/costs",
            json={
                "project_id": project_id,
                "provider": "baseline-provider",
                "category": "infrastructure",
                "amount_micros": 100_000_000,
                "currency": "BRL",
                "units": {},
                "observed_at": (now - timedelta(days=days_ago)).isoformat(),
                "metadata_json": {},
            },
        )
        assert baseline.status_code == 201

    spike = client.post(
        "/api/v1/holding/costs",
        json={
            "project_id": project_id,
            "provider": "spike-provider",
            "category": "llm",
            "amount_micros": 2_000_000_000,
            "currency": "BRL",
            "units": {"tokens": 1_000_000},
            "observed_at": now.isoformat(),
            "metadata_json": {},
        },
    )
    assert spike.status_code == 201

    analysis = client.post(f"/api/v1/holding/projects/{project_id}/finops/analyze")
    assert analysis.status_code == 200
    assert len(analysis.json()["anomalies"]) == 1
    assert analysis.json()["investigation_alerts_opened"] == 1
    assert analysis.json()["anomalies"][0]["ratio_to_baseline"] >= 2.0

    contract = client.get(f"/api/v1/holding/projects/{project_id}/contract")
    assert contract.status_code == 200
    alerts = contract.json()["alerts"]
    assert any(alert["source"] == "finops" for alert in alerts)

    completion = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json=_profile_payload("completed", budget_micros=10_000_000_000),
    )
    assert completion.status_code == 409


def test_venture_factory_gate_build_hold_and_reject(client: TestClient) -> None:
    candidates = [
        (
            "VENTURE_BUILD",
            90,
            {
                "plausible_positive": True,
                "cheap_validation": True,
                "gross_margin_target": 0.4,
            },
            {"controlled": True},
            "build",
        ),
        (
            "VENTURE_HOLD",
            90,
            {"plausible_positive": True},
            {"controlled": True},
            "hold",
        ),
        (
            "VENTURE_REJECT",
            50,
            {"plausible_positive": True, "cheap_validation": True},
            {"controlled": True},
            "reject",
        ),
    ]

    for key, automation, economics, risk, expected in candidates:
        created = client.post(
            "/api/v1/holding/ventures",
            json={
                "key": key,
                "name": key,
                "stage": "cheap-validation",
                "automation_pct": automation,
                "unit_economics": economics,
                "risk_summary": risk,
                "validation_cost_micros": 1_000_000,
                "decision": "research",
                "evidence": ["synthetic-market-analysis"],
            },
        )
        assert created.status_code == 201
        evaluated = client.post(f"/api/v1/holding/ventures/{key}/evaluate")
        assert evaluated.status_code == 200
        assert evaluated.json()["decision"] == expected
