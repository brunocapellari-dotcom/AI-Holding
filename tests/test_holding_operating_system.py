from datetime import UTC, datetime, timedelta

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


def _set_running_profile(client: TestClient, project_id: object) -> None:
    response = client.put(
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
    assert response.status_code == 200


def _create_collector(client: TestClient, project_id: object, key: str = "github") -> None:
    now = datetime.now(UTC).isoformat()
    response = client.put(
        f"/api/v1/holding/projects/{project_id}/collectors/{key}",
        json={
            "key": key,
            "source": key,
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
    assert response.status_code == 200


def test_project_contract_does_not_infer_completion_and_health_is_evidence_based(
    client: TestClient,
) -> None:
    project = _create_project(client)
    project_id = project["id"]

    contract = client.get(f"/api/v1/holding/projects/{project_id}/contract")
    assert contract.status_code == 200
    assert contract.json()["status"] == "planned"

    _set_running_profile(client, project_id)
    _create_collector(client, project_id)

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


def test_collector_execution_history_drives_aggregate_state(client: TestClient) -> None:
    project = _create_project(client, "COLLECTOR_HISTORY")
    project_id = project["id"]
    _set_running_profile(client, project_id)
    _create_collector(client, project_id)

    start = datetime.now(UTC)
    for index in range(3):
        failure = client.post(
            f"/api/v1/holding/projects/{project_id}/collectors/github/executions",
            json={
                "status": "failure",
                "started_at": (start + timedelta(seconds=index)).isoformat(),
                "finished_at": (start + timedelta(seconds=index + 1)).isoformat(),
                "latency_ms": 200,
                "records_seen": 0,
                "records_written": 0,
                "error_class": "UpstreamError",
                "error_message": "GitHub unavailable",
                "evidence": [{"attempt": index + 1}],
                "metadata_json": {},
            },
        )
        assert failure.status_code == 201

    collectors = client.get(f"/api/v1/holding/projects/{project_id}/collectors")
    assert collectors.status_code == 200
    assert collectors.json()[0]["status"] == "failing"
    assert collectors.json()[0]["consecutive_failures"] == 3

    health = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
    assert health.status_code == 200
    assert health.json()["state"] in {"degraded", "at_risk"}

    success = client.post(
        f"/api/v1/holding/projects/{project_id}/collectors/github/executions",
        json={
            "status": "success",
            "started_at": (start + timedelta(minutes=1)).isoformat(),
            "finished_at": (start + timedelta(minutes=1, seconds=1)).isoformat(),
            "latency_ms": 90,
            "records_seen": 4,
            "records_written": 4,
            "evidence": [{"sha": "abc123"}],
            "metadata_json": {},
        },
    )
    assert success.status_code == 201

    executions = client.get(f"/api/v1/holding/projects/{project_id}/collectors/github/executions")
    assert executions.status_code == 200
    assert len(executions.json()) == 4

    collectors = client.get(f"/api/v1/holding/projects/{project_id}/collectors")
    assert collectors.json()[0]["status"] == "healthy"
    assert collectors.json()[0]["consecutive_failures"] == 0


def test_finops_revenue_security_alerts_integrations_and_executive_state(
    client: TestClient,
) -> None:
    project = _create_project(client, "HOLDING_FINOPS")
    project_id = project["id"]
    _set_running_profile(client, project_id)

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
    assert summary.json()["totals_by_currency"] == {
        "BRL": 2_500_000,
        "USD": 1_000_000,
    }

    revenue = client.post(
        "/api/v1/holding/revenues",
        json={
            "project_id": project_id,
            "source": "subscription",
            "amount_micros": 5_000_000,
            "currency": "BRL",
            "observed_at": datetime.now(UTC).isoformat(),
            "metadata_json": {},
        },
    )
    assert revenue.status_code == 201
    revenue_summary = client.get(f"/api/v1/holding/revenues/summary?project_id={project_id}")
    assert revenue_summary.status_code == 200
    assert revenue_summary.json()["totals_by_currency"]["BRL"] == 5_000_000

    now = datetime.now(UTC)
    snapshot = client.post(
        "/api/v1/holding/financial-snapshots",
        json={
            "project_id": project_id,
            "currency": "BRL",
            "period_start": (now - timedelta(days=30)).isoformat(),
            "period_end": now.isoformat(),
            "revenue_micros": 5_000_000,
            "cost_micros": 2_500_000,
            "budget_micros": 15_000_000_000,
            "runway_days": 180,
            "payback_days": 90,
            "roi_estimate_bps": 1200,
            "confidence": 65,
            "assumptions": ["revenue remains stable"],
        },
    )
    assert snapshot.status_code == 201

    security = client.post(
        "/api/v1/holding/security/findings",
        json={
            "project_id": project_id,
            "source": "security-test-lab",
            "category": "auth-bypass",
            "severity": "high",
            "status": "open",
            "title": "Synthetic auth bypass finding",
            "description": "Controlled test finding for registry validation",
            "remediation": "Verify identity boundary",
            "evidence": ["synthetic-test"],
            "metadata_json": {"synthetic": True},
        },
    )
    assert security.status_code == 201
    findings = client.get(f"/api/v1/holding/security/findings?project_id={project_id}")
    assert findings.status_code == 200
    assert findings.json()[0]["severity"] == "high"

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
            "status": "unconfigured",
            "endpoint": None,
            "freshness_sla_seconds": 300,
            "metadata_json": {"contract": "v1", "runtime_evidence": False},
        },
    )
    assert integration.status_code == 200

    state = client.get("/api/v1/holding/executive-state")
    assert state.status_code == 200
    body = state.json()
    assert any(item["key"] == "HOLDING_FINOPS" for item in body["running"])
    assert body["costs"]["summary"]["totals_by_currency"]["BRL"] == 2_500_000
    assert body["revenues"]["summary"]["totals_by_currency"]["BRL"] == 5_000_000


def test_resource_portfolio_tool_and_venture_governance_gates(client: TestClient) -> None:
    project = _create_project(client, "HOLDING_GOVERNANCE")
    project_id = project["id"]

    budget_payload = {
        "project_id": project_id,
        "resource_type": "budget",
        "resource_key": "monthly-cap",
        "requested_units": 10_000_000,
        "allocated_units": 10_000_000,
        "unit": "BRL-micros",
        "status": "approved",
        "reason": "Controlled allocation",
        "metadata_json": {},
    }
    denied = client.post(
        "/api/v1/holding/resource-allocations",
        headers={"X-Actor": "pmo", "X-Actor-Type": "service-account"},
        json=budget_payload,
    )
    assert denied.status_code == 403

    allowed = client.post("/api/v1/holding/resource-allocations", json=budget_payload)
    assert allowed.status_code == 201

    sunset_payload = {
        "project_id": project_id,
        "classification": "sunset",
        "value_score": 10,
        "progress_score": 10,
        "cost_score": 90,
        "complexity_score": 90,
        "risk_score": 80,
        "monetization_score": 10,
        "dependency_score": 20,
        "requires_owner_approval": True,
        "rationale": "Synthetic sunset review",
        "evidence": ["portfolio-test"],
    }
    denied_sunset = client.post(
        "/api/v1/holding/portfolio-reviews",
        headers={"X-Actor": "ceo-ai", "X-Actor-Type": "service-account"},
        json=sunset_payload,
    )
    assert denied_sunset.status_code == 403
    allowed_sunset = client.post("/api/v1/holding/portfolio-reviews", json=sunset_payload)
    assert allowed_sunset.status_code == 201

    invalid_replace = client.post(
        "/api/v1/holding/tool-decisions",
        json={
            "key": "TEMPORAL_REPLACE",
            "tool_name": "Temporal",
            "capability": "durable-workflows",
            "classification": "replace",
            "benefit": "Durability",
            "maintenance_cost": "Operational runtime",
            "license": "MIT",
            "risk": "Adds another control plane",
            "rationale": "Must name what is replaced",
            "evidence": [],
        },
    )
    assert invalid_replace.status_code == 422

    tool = client.post(
        "/api/v1/holding/tool-decisions",
        json={
            "key": "TEMPORAL_BENCHMARK",
            "tool_name": "Temporal",
            "capability": "durable-workflows",
            "classification": "benchmark",
            "benefit": "Durable execution benchmark",
            "maintenance_cost": "Additional runtime if adopted",
            "license": "MIT",
            "risk": "Potential orchestration duplication",
            "rationale": "Benchmark before any replacement",
            "evidence": ["github:temporalio/temporal"],
        },
    )
    assert tool.status_code == 201

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


def test_registry_exposes_real_operational_contract_not_legacy_status(client: TestClient) -> None:
    project = _create_project(client, "REGISTRY_EVIDENCE")
    project_id = project["id"]

    registry = client.get("/api/v1/holding/projects/registry")
    assert registry.status_code == 200
    row = next(item for item in registry.json() if item["project_key"] == "REGISTRY_EVIDENCE")
    assert row["legacy_status"] == "active"
    assert row["operational_status"] == "planned"

    _set_running_profile(client, project_id)
    registry = client.get("/api/v1/holding/projects/registry")
    row = next(item for item in registry.json() if item["project_key"] == "REGISTRY_EVIDENCE")
    assert row["operational_status"] == "running"
