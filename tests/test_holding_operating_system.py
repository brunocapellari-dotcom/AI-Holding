from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _create_project(client: TestClient, key: str = "HOLDING_E2E") -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": f"{key} Project",
            "priority": 1,
            "autonomy_level": 4,
            "strategic_goal": "Validate the complete Holding operating contract",
            "metadata_json": {"capabilities": ["project.health", "project.cost"]},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_project_contract_does_not_infer_completion_and_health_is_evidence_based(
    client: TestClient,
) -> None:
    project = _create_project(client)
    project_id = project["id"]

    contract = client.get(f"/api/v1/holding/projects/{project_id}/contract")
    assert contract.status_code == 200
    assert contract.json()["status"] == "planned"

    profile = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json={
            "mission": "Operate the Holding control plane",
            "operational_status": "running",
            "knowledge_namespace": "holding",
            "current_phase": "final-integration",
            "security_level": "restricted",
            "budget_micros": 15_000_000_000,
            "budget_currency": "BRL",
            "metadata_json": {},
        },
    )
    assert profile.status_code == 200
    assert profile.json()["operational_status"] == "running"

    now = datetime.now(UTC).isoformat()
    collector = client.put(
        f"/api/v1/holding/projects/{project_id}/collectors/github",
        json={
            "key": "github",
            "source": "github",
            "data_type": "repository_state",
            "frequency_seconds": 300,
            "freshness_sla_seconds": 900,
            "retry_policy": {"max_attempts": 3},
            "status": "healthy",
            "last_success_at": now,
            "last_failure_at": None,
            "last_latency_ms": 100,
            "consecutive_failures": 0,
            "metadata_json": {},
        },
    )
    assert collector.status_code == 200

    health = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
    assert health.status_code == 200
    assert health.json()["state"] == "healthy"
    assert health.json()["score"] == 100

    risk = client.post(
        "/api/v1/holding/risks",
        json={
            "project_id": project_id,
            "key": "RISK_VENDOR",
            "description": "Critical vendor dependency",
            "probability": 70,
            "impact": 5,
            "severity": "critical",
            "mitigation": "Maintain a tested exit path",
            "owner": "risk-ai",
            "status": "open",
            "metadata_json": {},
        },
    )
    assert risk.status_code == 201

    dependency = client.post(
        "/api/v1/holding/dependencies",
        json={
            "source_type": "project",
            "source_key": "HOLDING_E2E",
            "target_type": "service",
            "target_key": "critical-service",
            "criticality": 5,
            "blocking": True,
            "status": "blocked",
            "metadata_json": {},
        },
    )
    assert dependency.status_code == 201

    blocked_health = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
    assert blocked_health.status_code == 200
    assert blocked_health.json()["state"] == "blocked"
    assert blocked_health.json()["score"] < 100


def test_finops_alert_dedup_integrations_venture_and_executive_state(client: TestClient) -> None:
    project = _create_project(client, "HOLDING_FINOPS")
    project_id = project["id"]
    client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json={
            "mission": "Measure costs",
            "operational_status": "running",
            "security_level": "internal",
            "budget_micros": 1_000_000_000,
            "budget_currency": "BRL",
            "metadata_json": {},
        },
    )

    for currency, amount in [("BRL", 2_500_000), ("USD", 1_000_000)]:
        response = client.post(
            "/api/v1/holding/costs",
            json={
                "project_id": project_id,
                "provider": "llm-provider",
                "category": "llm",
                "amount_micros": amount,
                "currency": currency,
                "units": {"tokens": 1000},
                "observed_at": datetime.now(UTC).isoformat(),
                "metadata_json": {},
            },
        )
        assert response.status_code == 201

    summary = client.get(f"/api/v1/holding/costs/summary?project_id={project_id}")
    assert summary.status_code == 200
    assert summary.json()["totals_by_currency"] == {"BRL": 2_500_000, "USD": 1_000_000}

    alert_payload = {
        "project_id": project_id,
        "level": "action_required",
        "source": "finops",
        "dedupe_key": "cost-spike:HOLDING_FINOPS",
        "title": "Cost spike detected",
        "details": {"ratio": 2.1},
        "status": "active",
    }
    first = client.post("/api/v1/holding/alerts", json=alert_payload)
    second = client.post("/api/v1/holding/alerts", json=alert_payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["occurrences"] == 2

    integration = client.put(
        "/api/v1/holding/integrations/hermes",
        json={
            "service_key": "hermes",
            "kind": "ai-platform",
            "status": "healthy",
            "endpoint": "https://hermes.internal",
            "freshness_sla_seconds": 300,
            "metadata_json": {"contract": "v1"},
        },
    )
    assert integration.status_code == 200

    venture = client.post(
        "/api/v1/holding/ventures",
        json={
            "key": "AUTO_B2B",
            "name": "Automated B2B venture",
            "stage": "cheap-validation",
            "automation_pct": 90,
            "unit_economics": {"gross_margin_target": 0.6},
            "risk_summary": {"legal": "controlled"},
            "validation_cost_micros": 50_000_000,
            "decision": "research",
            "evidence": ["market-study"],
        },
    )
    assert venture.status_code == 201

    state = client.get("/api/v1/holding/executive-state")
    assert state.status_code == 200
    body = state.json()
    assert any(item["key"] == "HOLDING_FINOPS" for item in body["running"])
    assert body["costs"]["summary"]["totals_by_currency"]["BRL"] == 2_500_000
