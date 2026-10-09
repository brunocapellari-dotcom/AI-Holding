from datetime import UTC, datetime

from fastapi.testclient import TestClient


def _project(client: TestClient, key: str = "REGISTRY_COVERAGE") -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": key,
            "priority": 1,
            "autonomy_level": 3,
            "strategic_goal": "Exercise corporate registries with audited evidence.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_corporate_registries_create_update_filter_and_validate(client: TestClient) -> None:
    project = _project(client)
    project_id = project["id"]
    missing_project = "00000000-0000-0000-0000-000000000099"

    directory = client.get("/api/v1/holding/registries")
    assert directory.status_code == 200

    tool = {
        "key": "ruff",
        "name": "Ruff",
        "capability": "code-quality",
        "status": "approved",
        "evidence": ["ci"],
    }
    assert client.put("/api/v1/holding/registries/tools/wrong", json=tool).status_code == 400
    created = client.put("/api/v1/holding/registries/tools/ruff", json=tool)
    assert created.status_code == 200, created.text
    tool["name"] = "Ruff Linter"
    assert client.put("/api/v1/holding/registries/tools/ruff", json=tool).status_code == 200
    tools = client.get(
        "/api/v1/holding/registries/tools",
        params={"status": " approved ", "capability": " code-quality ", "limit": 999, "offset": -1},
    )
    assert tools.status_code == 200
    assert len(tools.json()) == 1

    source = {
        "key": "usda",
        "name": "USDA",
        "source_type": "official-api",
        "status": "approved",
        "authority": "primary",
        "freshness_sla_seconds": 3600,
        "evidence": ["official"],
    }
    assert client.put("/api/v1/holding/registries/sources/nope", json=source).status_code == 400
    assert client.put("/api/v1/holding/registries/sources/usda", json=source).status_code == 200
    source["terms_review_status"] = "approved"
    assert client.put("/api/v1/holding/registries/sources/usda", json=source).status_code == 200
    sources = client.get(
        "/api/v1/holding/registries/sources",
        params={"status": "approved", "authority": "primary"},
    )
    assert sources.status_code == 200
    assert len(sources.json()) == 1

    license_payload = {
        "spdx_id": "Apache-2.0",
        "name": "Apache License 2.0",
        "classification": "permissive",
        "usage_policy": "approved",
    }
    assert (
        client.put("/api/v1/holding/registries/licenses/MIT", json=license_payload).status_code
        == 400
    )
    assert (
        client.put(
            "/api/v1/holding/registries/licenses/Apache-2.0",
            json={**license_payload, "reviewed_at": datetime.now(UTC).isoformat()},
        ).status_code
        == 422
    )
    license_created = client.put(
        "/api/v1/holding/registries/licenses/Apache-2.0",
        json=license_payload,
    )
    assert license_created.status_code == 200
    license_payload["reviewed_by"] = "OWNER"
    license_payload["reviewed_at"] = datetime.now(UTC).isoformat()
    license_updated = client.put(
        "/api/v1/holding/registries/licenses/Apache-2.0",
        json=license_payload,
    )
    assert license_updated.status_code == 200
    assert (
        client.get(
            "/api/v1/holding/registries/licenses", params={"usage_policy": " approved "}
        ).status_code
        == 200
    )

    model = {
        "key": "gpt-control",
        "provider": "openai",
        "model_id": "control-model",
        "status": "candidate",
        "intended_uses": ["governance-summary"],
    }
    assert client.put("/api/v1/holding/registries/models/wrong", json=model).status_code == 400
    model_created = client.put(
        "/api/v1/holding/registries/models/gpt-control",
        json=model,
    )
    assert model_created.status_code == 200
    model["status"] = "approved"
    model_updated = client.put(
        "/api/v1/holding/registries/models/gpt-control",
        json=model,
    )
    assert model_updated.status_code == 200
    models = client.get(
        "/api/v1/holding/registries/models",
        params={"provider": " openai ", "status": " approved "},
    )
    assert models.status_code == 200
    assert len(models.json()) == 1

    evaluation = {
        "key": "release-e2e",
        "project_id": project_id,
        "name": "Release E2E",
        "evaluation_type": "regression",
        "status": "active",
        "evidence": ["run-1"],
    }
    assert (
        client.put("/api/v1/holding/registries/evaluations/wrong", json=evaluation).status_code
        == 400
    )
    assert (
        client.put(
            "/api/v1/holding/registries/evaluations/missing-project",
            json={**evaluation, "key": "missing-project", "project_id": missing_project},
        ).status_code
        == 404
    )
    evaluation_created = client.put(
        "/api/v1/holding/registries/evaluations/release-e2e",
        json=evaluation,
    )
    assert evaluation_created.status_code == 200
    evaluation["latest_result"] = {"passed": True}
    evaluation_updated = client.put(
        "/api/v1/holding/registries/evaluations/release-e2e",
        json=evaluation,
    )
    assert evaluation_updated.status_code == 200
    evaluations = client.get(
        "/api/v1/holding/registries/evaluations",
        params={"project_id": project_id, "evaluation_type": " regression "},
    )
    assert evaluations.status_code == 200
    assert len(evaluations.json()) == 1

    adr = {
        "key": "adr-control-plane",
        "title": "Control plane ownership boundary",
        "status": "proposed",
        "document_ref": "docs/adr/control-plane.md",
        "rationale": "Holding governs while Hermes orchestrates.",
        "evidence": ["mission"],
    }
    assert (
        client.put("/api/v1/holding/registries/architecture-decisions/wrong", json=adr).status_code
        == 400
    )
    invalid_final = {**adr, "status": "accepted"}
    assert (
        client.put(
            "/api/v1/holding/registries/architecture-decisions/adr-control-plane",
            json=invalid_final,
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/v1/holding/registries/architecture-decisions/adr-control-plane", json=adr
        ).status_code
        == 200
    )
    adr["status"] = "accepted"
    adr["decided_at"] = datetime.now(UTC).isoformat()
    assert (
        client.put(
            "/api/v1/holding/registries/architecture-decisions/adr-control-plane", json=adr
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/v1/holding/registries/architecture-decisions",
            params={"status": " accepted "},
        ).status_code
        == 200
    )

    contract = {
        "key": "holding-events-v1",
        "project_id": project_id,
        "dataset_key": "holding-events",
        "status": "active",
        "contract_ref": "schemas/holding-events.json",
        "version": "1",
        "required_checks": ["schema", "freshness"],
        "evidence": ["contract-test"],
    }
    assert (
        client.put("/api/v1/holding/registries/data-contracts/wrong", json=contract).status_code
        == 400
    )
    assert (
        client.put(
            "/api/v1/holding/registries/data-contracts/missing-project",
            json={**contract, "key": "missing-project", "project_id": missing_project},
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/holding/registries/data-contracts/holding-events-v1", json=contract
        ).status_code
        == 200
    )
    contract["latest_result"] = {"status": "pass"}
    assert (
        client.put(
            "/api/v1/holding/registries/data-contracts/holding-events-v1", json=contract
        ).status_code
        == 200
    )
    contracts = client.get(
        "/api/v1/holding/registries/data-contracts",
        params={"project_id": project_id, "status": " active "},
    )
    assert contracts.status_code == 200
    assert len(contracts.json()) == 1
