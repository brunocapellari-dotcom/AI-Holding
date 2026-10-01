from fastapi.testclient import TestClient


def _create_project(client: TestClient, key: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": key,
            "priority": 1,
            "autonomy_level": 4,
            "strategic_goal": "Validate security propagation",
            "metadata_json": {},
        },
    )
    assert response.status_code == 201
    return response.json()


def _set_running(client: TestClient, project_id: object) -> None:
    response = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json={
            "mission": "Security acceptance",
            "operational_status": "running",
            "security_level": "restricted",
            "budget_micros": 0,
            "budget_currency": "BRL",
            "metadata_json": {},
        },
    )
    assert response.status_code == 200


def _verify_acceptance(client: TestClient, project_id: object) -> None:
    milestone = client.post(
        f"/api/v1/projects/{project_id}/milestones",
        json={
            "key": "SECURITY_FINAL",
            "title": "Security final",
            "objective": "Verify release evidence",
            "weight": 100,
        },
    )
    assert milestone.status_code == 201
    milestone_id = milestone.json()["id"]
    criterion = client.post(
        f"/api/v1/projects/{project_id}/milestones/{milestone_id}/criteria",
        json={
            "key": "SECURITY_GATE",
            "description": "Release security gate",
            "weight": 100,
        },
    )
    assert criterion.status_code == 201
    criterion_id = criterion.json()["id"]
    verified = client.post(
        f"/api/v1/projects/{project_id}/milestones/{milestone_id}/criteria/{criterion_id}/verify",
        json={"evidence": ["security-gate-evidence"]},
    )
    assert verified.status_code == 200


def test_high_security_finding_degrades_health_and_blocks_completion(
    client: TestClient,
) -> None:
    project = _create_project(client, "SECURITY_HIGH")
    project_id = project["id"]
    _set_running(client, project_id)
    _verify_acceptance(client, project_id)

    finding = client.post(
        "/api/v1/holding/security/findings",
        json={
            "project_id": project_id,
            "source": "security-test-lab",
            "category": "privilege-escalation",
            "severity": "high",
            "status": "open",
            "title": "Synthetic high finding",
            "description": "Controlled high-severity acceptance finding",
            "remediation": "Close before release",
            "evidence": ["synthetic"],
            "metadata_json": {"synthetic": True},
        },
    )
    assert finding.status_code == 201

    health = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
    assert health.status_code == 200
    assert health.json()["state"] == "degraded"
    assert health.json()["dimensions"]["security"]["high"] == 1

    gate = client.get(f"/api/v1/holding/projects/{project_id}/completion-gate")
    assert gate.status_code == 200
    assert gate.json()["accepted"] is False
    assert gate.json()["blocking_security_findings"] == 1

    completed = client.put(
        f"/api/v1/holding/projects/{project_id}/profile",
        json={
            "mission": "Security acceptance",
            "operational_status": "completed",
            "security_level": "restricted",
            "budget_micros": 0,
            "budget_currency": "BRL",
            "metadata_json": {},
        },
    )
    assert completed.status_code == 409


def test_critical_security_finding_forces_at_risk(client: TestClient) -> None:
    project = _create_project(client, "SECURITY_CRITICAL")
    project_id = project["id"]
    _set_running(client, project_id)

    finding = client.post(
        "/api/v1/holding/security/findings",
        json={
            "project_id": project_id,
            "source": "security-test-lab",
            "category": "secret-exfiltration",
            "severity": "critical",
            "status": "open",
            "title": "Synthetic critical finding",
            "description": "Controlled critical acceptance finding",
            "remediation": "Block release",
            "evidence": ["synthetic"],
            "metadata_json": {"synthetic": True},
        },
    )
    assert finding.status_code == 201

    health = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
    assert health.status_code == 200
    assert health.json()["state"] == "at_risk"
    assert health.json()["dimensions"]["security"]["critical"] == 1
