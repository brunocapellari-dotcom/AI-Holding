from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import settings


def _claim_payload(
    *,
    statement: str = (
        "Freight pressure rises when export demand accelerates while truck supply tightens."
    ),
    namespace: str = "agrolog_mt",
) -> dict[str, object]:
    return {
        "namespace": namespace,
        "statement": statement,
        "epistemic_status": "inferred",
        "confidence": 72,
        "source_name": "AgroLog methodology",
        "source_uri": "https://example.invalid/methodology",
        "evidence": [
            {
                "source": "internal-analysis",
                "locator": "freight-pressure-model-v1",
                "checksum": "sha256:abc",
            }
        ],
        "tags": ["freight", "logistics"],
    }


def _create_claim(client: TestClient, **kwargs: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/knowledge/claims",
        json=_claim_payload(**kwargs),
    )
    assert response.status_code == 201
    return response.json()["claim"]


def _transition(client: TestClient, claim_id: str, lifecycle: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/knowledge/claims/{claim_id}/transition",
        json={"lifecycle_status": lifecycle},
    )
    assert response.status_code == 200
    return response.json()


def test_knowledge_ingest_deduplicates_and_merges_evidence(client: TestClient) -> None:
    first = client.post("/api/v1/knowledge/claims", json=_claim_payload())
    assert first.status_code == 201
    body = first.json()
    assert body["created"] is True
    assert body["claim"]["lifecycle_status"] == "raw"
    assert body["claim"]["confidence"] == 72

    second_payload = _claim_payload()
    second_payload["confidence"] = 80
    second_payload["epistemic_status"] = "estimated"
    second_payload["evidence"] = [
        {
            "source": "validation-run",
            "locator": "2026-09-14",
            "checksum": "sha256:def",
        }
    ]
    second = client.post("/api/v1/knowledge/claims", json=second_payload)
    assert second.status_code == 201
    merged = second.json()
    assert merged["created"] is False
    assert merged["merged_evidence"] == 1
    assert merged["claim"]["confidence"] == 80
    assert len(merged["claim"]["evidence"]) == 2
    assert merged["claim"]["epistemic_status"] == "inferred"
    assert merged["claim"]["metadata_json"]["ingest_conflicts"]


def test_knowledge_lifecycle_context_outcome_and_export(
    client: TestClient,
    tmp_path: Path,
) -> None:
    claim = _create_claim(client)
    claim_id = str(claim["id"])

    for lifecycle in ("candidate", "validated", "canonical"):
        response = _transition(client, claim_id, lifecycle)
        assert response["lifecycle_status"] == lifecycle

    same = _transition(client, claim_id, "canonical")
    assert same["lifecycle_status"] == "canonical"

    context = client.get(
        "/api/v1/knowledge/context",
        params={"namespace": "agrolog_mt", "q": "truck supply"},
    )
    assert context.status_code == 200
    assert [item["id"] for item in context.json()] == [claim_id]

    outcome = client.post(
        f"/api/v1/knowledge/claims/{claim_id}/outcomes",
        json={
            "verdict": "partially_confirmed",
            "observed_result": "Direction was correct, magnitude was lower than projected.",
            "error_metric": 5.0,
            "evidence": [{"source": "postmortem", "locator": "week-37"}],
        },
    )
    assert outcome.status_code == 201
    assert outcome.json()["verdict"] == "partially_confirmed"

    outcomes = client.get(f"/api/v1/knowledge/claims/{claim_id}/outcomes")
    assert outcomes.status_code == 200
    assert len(outcomes.json()) == 1

    refreshed = client.get(f"/api/v1/knowledge/claims/{claim_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["metadata_json"]["outcome_counts"]["partially_confirmed"] == 1

    rendered = client.get(f"/api/v1/knowledge/claims/{claim_id}/markdown")
    assert rendered.status_code == 200
    assert "# Knowledge Claim" in rendered.json()["markdown"]

    old_vault = settings.obsidian_vault_path
    old_root = settings.obsidian_knowledge_root
    settings.obsidian_vault_path = str(tmp_path)
    settings.obsidian_knowledge_root = "Segundo Cerebro"
    try:
        exported = client.post(f"/api/v1/knowledge/claims/{claim_id}/export")
    finally:
        settings.obsidian_vault_path = old_vault
        settings.obsidian_knowledge_root = old_root

    assert exported.status_code == 200
    relative_path = exported.json()["relative_path"]
    target = tmp_path / relative_path
    assert target.exists()
    markdown = target.read_text(encoding="utf-8")
    assert "# Knowledge Claim" in markdown
    assert "partially_confirmed" in markdown


def test_supersession_preserves_history(client: TestClient) -> None:
    old = _create_claim(
        client,
        statement="The canonical freight methodology uses model version one.",
    )
    old_id = str(old["id"])
    for lifecycle in ("candidate", "validated", "canonical"):
        _transition(client, old_id, lifecycle)

    new = _create_claim(
        client,
        statement="The canonical freight methodology uses model version two.",
    )
    new_id = str(new["id"])
    _transition(client, new_id, "candidate")
    _transition(client, new_id, "validated")
    promoted = client.post(
        f"/api/v1/knowledge/claims/{new_id}/transition",
        json={"lifecycle_status": "canonical", "supersedes_id": old_id},
    )
    assert promoted.status_code == 200
    assert promoted.json()["supersedes_id"] == old_id

    previous = client.get(f"/api/v1/knowledge/claims/{old_id}")
    assert previous.status_code == 200
    assert previous.json()["lifecycle_status"] == "superseded"


def test_cross_namespace_supersession_is_rejected(client: TestClient) -> None:
    old = _create_claim(
        client,
        statement="Shared inflation definition for finance.",
        namespace="mercado_financeiro",
    )
    old_id = str(old["id"])
    for lifecycle in ("candidate", "validated", "canonical"):
        _transition(client, old_id, lifecycle)

    new = _create_claim(
        client,
        statement="Shared inflation definition for agriculture.",
        namespace="agrolog_mt",
    )
    new_id = str(new["id"])
    _transition(client, new_id, "candidate")
    _transition(client, new_id, "validated")
    response = client.post(
        f"/api/v1/knowledge/claims/{new_id}/transition",
        json={"lifecycle_status": "canonical", "supersedes_id": old_id},
    )
    assert response.status_code == 409


def test_invalid_knowledge_transition_and_missing_claim_are_rejected(
    client: TestClient,
) -> None:
    claim = _create_claim(client)
    claim_id = str(claim["id"])
    invalid = client.post(
        f"/api/v1/knowledge/claims/{claim_id}/transition",
        json={"lifecycle_status": "canonical"},
    )
    assert invalid.status_code == 409

    missing = client.get(f"/api/v1/knowledge/claims/{uuid4()}")
    assert missing.status_code == 404


def test_context_excludes_expired_and_unvalidated_claims(client: TestClient) -> None:
    raw = _claim_payload(statement="Raw claim must not enter trusted context.")
    raw_response = client.post("/api/v1/knowledge/claims", json=raw)
    assert raw_response.status_code == 201

    expired = _claim_payload(statement="Expired canonical claim must not be retrieved.")
    expired["valid_from"] = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    expired["valid_until"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    expired_response = client.post("/api/v1/knowledge/claims", json=expired)
    assert expired_response.status_code == 201
    expired_id = expired_response.json()["claim"]["id"]
    for lifecycle in ("candidate", "validated", "canonical"):
        _transition(client, expired_id, lifecycle)

    context = client.get(
        "/api/v1/knowledge/context",
        params={"namespace": "agrolog_mt"},
    )
    assert context.status_code == 200
    assert context.json() == []


def test_export_requires_configuration_and_approved_lifecycle(
    client: TestClient,
    tmp_path: Path,
) -> None:
    claim = _create_claim(client)
    claim_id = str(claim["id"])

    old_vault = settings.obsidian_vault_path
    settings.obsidian_vault_path = None
    try:
        unconfigured = client.post(f"/api/v1/knowledge/claims/{claim_id}/export")
    finally:
        settings.obsidian_vault_path = old_vault
    assert unconfigured.status_code == 503

    old_vault = settings.obsidian_vault_path
    settings.obsidian_vault_path = str(tmp_path)
    try:
        raw_export = client.post(f"/api/v1/knowledge/claims/{claim_id}/export")
    finally:
        settings.obsidian_vault_path = old_vault
    assert raw_export.status_code == 409


def test_invalid_references_and_validity_window_are_rejected(client: TestClient) -> None:
    bad_project = _claim_payload(statement="Claim with missing project reference.")
    bad_project["project_id"] = str(uuid4())
    response = client.post("/api/v1/knowledge/claims", json=bad_project)
    assert response.status_code == 404

    invalid_window = _claim_payload(statement="Claim with invalid validity window.")
    invalid_window["valid_from"] = datetime.now(UTC).isoformat()
    invalid_window["valid_until"] = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    response = client.post("/api/v1/knowledge/claims", json=invalid_window)
    assert response.status_code == 422


def test_list_claims_filters_by_namespace_and_lifecycle(client: TestClient) -> None:
    claim = _create_claim(
        client,
        statement="A finance-only canonical knowledge statement.",
        namespace="mercado_financeiro",
    )
    claim_id = str(claim["id"])
    for lifecycle in ("candidate", "validated"):
        _transition(client, claim_id, lifecycle)

    response = client.get(
        "/api/v1/knowledge/claims",
        params={
            "namespace": "mercado_financeiro",
            "lifecycle_status": "validated",
            "q": "finance-only",
        },
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [claim_id]
