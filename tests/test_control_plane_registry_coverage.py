from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _project(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": "CONTROL_REGISTRY_COVERAGE",
            "name": "Control Registry Coverage",
            "priority": 0,
            "autonomy_level": 4,
            "strategic_goal": "Exercise operational registries and evidence gates.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_operational_registries_cover_errors_updates_and_audit_paths(client: TestClient) -> None:
    project = _project(client)
    project_id = project["id"]
    base = "/api/v1/holding/control-plane"

    assert client.get(f"{base}/releases").status_code == 200
    assert (
        client.get(
            f"{base}/releases/00000000-0000-0000-0000-000000000099/gates"
        ).status_code
        == 404
    )

    release_payload = {
        "project_id": project_id,
        "name": "CONTROL-1",
        "scope": ["registries"],
        "dependencies": [],
        "commercial_status": "NOT_READY",
        "metadata_json": {},
    }
    created = client.post(f"{base}/releases", json=release_payload)
    assert created.status_code == 201, created.text
    release = created.json()
    release_id = release["id"]
    assert client.post(f"{base}/releases", json=release_payload).status_code == 409

    filtered = client.get(f"{base}/releases", params={"project_id": project_id})
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    started = client.post(
        f"{base}/releases/{release_id}/status",
        json={"status": "IN_PROGRESS"},
    )
    assert started.status_code == 200
    assert (
        client.post(
            f"{base}/releases/{release_id}/status",
            json={"status": "IN_PROGRESS", "commercial_status": "SELLABLE"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"{base}/releases/00000000-0000-0000-0000-000000000099/status",
            json={"status": "IN_PROGRESS"},
        ).status_code
        == 404
    )

    gates = client.get(f"{base}/releases/{release_id}/gates")
    assert gates.status_code == 200
    assert len(gates.json()) == 6
    assert (
        client.put(
            f"{base}/releases/{release_id}/gates/CODE",
            json={"gate_type": "TEST", "status": "PASS", "evidence_required": True},
        ).status_code
        == 400
    )
    assert (
        client.put(
            f"{base}/releases/{release_id}/gates/CODE",
            json={"gate_type": "CODE", "status": "PASS", "evidence_required": True},
        ).status_code
        == 409
    )

    missing_project_evidence = client.post(
        f"{base}/evidence",
        json={
            "project_id": "00000000-0000-0000-0000-000000000099",
            "kind": "COMMIT",
            "source": "github",
            "artifact_reference": "deadbeef",
        },
    )
    assert missing_project_evidence.status_code == 404

    evidence = client.post(
        f"{base}/evidence",
        json={
            "project_id": project_id,
            "release_id": release_id,
            "kind": "COMMIT",
            "source": "github",
            "artifact_reference": "abcdef1234567",
        },
    )
    assert evidence.status_code == 201, evidence.text
    evidence_id = evidence.json()["id"]
    assert (
        client.post(
            f"{base}/evidence/00000000-0000-0000-0000-000000000099/verify",
            json={"verification_status": "VERIFIED"},
        ).status_code
        == 404
    )
    verified = client.post(
        f"{base}/evidence/{evidence_id}/verify",
        json={"verification_status": "VERIFIED"},
    )
    assert verified.status_code == 200

    passed = client.put(
        f"{base}/releases/{release_id}/gates/CODE",
        json={
            "gate_type": "CODE",
            "status": "PASS",
            "evidence_required": True,
            "notes": "commit verified",
        },
    )
    assert passed.status_code == 200
    reset = client.put(
        f"{base}/releases/{release_id}/gates/CODE",
        json={"gate_type": "CODE", "status": "IN_PROGRESS", "evidence_required": True},
    )
    assert reset.status_code == 200

    service_payload = {
        "project_id": project_id,
        "name": "api",
        "environment": "production",
        "version": "v1",
        "endpoint": "https://example.invalid",
        "status": "HEALTHY",
        "last_health_check": datetime.now(UTC).isoformat(),
        "dependencies": [],
        "owner": "AI_HOLDING",
        "metadata_json": {},
    }
    service = client.put(f"{base}/services", json=service_payload)
    assert service.status_code == 200, service.text
    service_payload["status"] = "DEGRADED"
    service_update = client.put(f"{base}/services", json=service_payload)
    assert service_update.status_code == 200
    service_id = service_update.json()["id"]

    deployment_payload = {
        "project_id": project_id,
        "service_id": service_id,
        "release_id": release_id,
        "version": "v1",
        "commit_sha": "abcdef1234567",
        "environment": "production",
        "deployment_ref": "cloud-run:coverage:v1",
        "started_at": datetime.now(UTC).isoformat(),
        "status": "HEALTHY",
        "metadata_json": {},
    }
    deployment = client.post(f"{base}/deployments", json=deployment_payload)
    assert deployment.status_code == 201, deployment.text
    assert client.post(f"{base}/deployments", json=deployment_payload).status_code == 409

    test_record = client.post(
        f"{base}/tests",
        json={
            "project_id": project_id,
            "release_id": release_id,
            "suite": "smoke",
            "test_type": "SMOKE",
            "commit_sha": "abcdef1234567",
            "environment": "production",
            "result": "PASS",
            "failures": [],
            "metadata_json": {},
        },
    )
    assert test_record.status_code == 201, test_record.text

    blocker = client.post(
        f"{base}/blockers",
        json={
            "project_id": project_id,
            "release_id": release_id,
            "blocker_type": "TECHNICAL",
            "description": "Synthetic operational blocker",
            "impact": "Release is blocked",
            "owner": "PMO_IA",
            "action_required": "Resolve synthetic blocker",
            "priority": "P1",
            "metadata_json": {},
        },
    )
    assert blocker.status_code == 201, blocker.text
    blocker_id = blocker.json()["id"]
    assert (
        client.post(
            f"{base}/blockers/00000000-0000-0000-0000-000000000099/resolve"
        ).status_code
        == 404
    )
    assert client.post(f"{base}/blockers/{blocker_id}/resolve").status_code == 200

    bad_governance = client.put(
        f"{base}/projects/{project_id}/governance",
        json={
            "declared_status": "ACTIVE",
            "priority_tier": "P0",
            "current_release_id": "00000000-0000-0000-0000-000000000099",
        },
    )
    assert bad_governance.status_code == 400

    governance = client.put(
        f"{base}/projects/{project_id}/governance",
        json={
            "declared_status": "ACTIVE",
            "priority_tier": "P0",
            "current_release_id": release_id,
            "commercial_status": "NOT_READY",
            "monthly_budget_micros": 1000000,
            "next_best_action": "Close gates",
            "metadata_json": {},
        },
    )
    assert governance.status_code == 200, governance.text
    recomputed = client.post(f"{base}/projects/{project_id}/recompute")
    assert recomputed.status_code == 200

    owner_view = client.get(f"{base}/owner-view")
    assert owner_view.status_code == 200
    assert any(row["project_id"] == project_id for row in owner_view.json()["projects"])
    assert client.get(f"{base}/human-actions").status_code == 200
