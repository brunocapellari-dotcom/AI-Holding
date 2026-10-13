from fastapi.testclient import TestClient


def _project(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": "GOVERNANCE_COVERAGE",
            "name": "Governance Coverage",
            "priority": 1,
            "autonomy_level": 3,
            "strategic_goal": "Exercise capability autonomy governance.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_capability_autonomy_validation_update_listing_and_review(client: TestClient) -> None:
    project = _project(client)
    project_id = project["id"]
    path = f"/api/v1/holding/governance/projects/{project_id}/capabilities/deploy"

    service_actor = client.put(
        path,
        headers={"X-Actor": "worker", "X-Actor-Type": "service-account"},
        json={
            "capability_key": "deploy",
            "autonomy_level": 2,
            "rationale": "Service actor must not change governance.",
        },
    )
    assert service_actor.status_code == 403

    mismatch = client.put(
        path,
        json={
            "capability_key": "other",
            "autonomy_level": 2,
            "rationale": "Mismatch must fail.",
        },
    )
    assert mismatch.status_code == 400

    no_constraints = client.put(
        path,
        json={
            "capability_key": "deploy",
            "autonomy_level": 4,
            "rationale": "High autonomy needs constraints.",
        },
    )
    assert no_constraints.status_code == 422

    no_evidence = client.put(
        path,
        json={
            "capability_key": "deploy",
            "autonomy_level": 4,
            "constraints": ["production gate"],
            "rationale": "High autonomy needs evidence.",
        },
    )
    assert no_evidence.status_code == 422

    payload = {
        "capability_key": "deploy",
        "autonomy_level": 4,
        "status": "validated",
        "authority_scope": {"environment": "staging"},
        "constraints": ["immutable image", "green gates"],
        "evidence": ["ci-run"],
        "rationale": "Bounded deployment autonomy.",
    }
    created = client.put(path, json=payload)
    assert created.status_code == 200, created.text
    assert created.json()["reviewed_by"] is not None

    payload["status"] = "suspended"
    payload["autonomy_level"] = 2
    updated = client.put(path, json=payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["reviewed_by"] is None

    listed = client.get(f"/api/v1/holding/governance/projects/{project_id}/capabilities")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    review = client.post(f"/api/v1/holding/governance/projects/{project_id}/review")
    assert review.status_code == 200, review.text
    assert review.json()["project_id"] == project_id

    missing = client.get(
        "/api/v1/holding/governance/projects/00000000-0000-0000-0000-000000000099/capabilities"
    )
    assert missing.status_code == 404
