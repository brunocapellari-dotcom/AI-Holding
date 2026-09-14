from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings


def _claim_payload() -> dict[str, object]:
    return {
        "namespace": "agrolog_mt",
        "statement": "Freight pressure rises when export demand accelerates while truck supply tightens.",
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


def test_knowledge_ingest_deduplicates_and_merges_evidence(client: TestClient) -> None:
    first = client.post("/api/v1/knowledge/claims", json=_claim_payload())
    assert first.status_code == 201
    body = first.json()
    assert body["created"] is True
    assert body["claim"]["lifecycle_status"] == "raw"
    assert body["claim"]["confidence"] == 72

    second_payload = _claim_payload()
    second_payload["confidence"] = 80
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


def test_knowledge_lifecycle_context_outcome_and_export(
    client: TestClient,
    tmp_path: Path,
) -> None:
    created = client.post("/api/v1/knowledge/claims", json=_claim_payload())
    claim_id = created.json()["claim"]["id"]

    for lifecycle in ("candidate", "validated", "canonical"):
        response = client.post(
            f"/api/v1/knowledge/claims/{claim_id}/transition",
            json={"lifecycle_status": lifecycle},
        )
        assert response.status_code == 200
        assert response.json()["lifecycle_status"] == lifecycle

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

    refreshed = client.get(f"/api/v1/knowledge/claims/{claim_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["metadata_json"]["outcome_counts"]["partially_confirmed"] == 1

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


def test_invalid_knowledge_transition_is_rejected(client: TestClient) -> None:
    created = client.post("/api/v1/knowledge/claims", json=_claim_payload())
    claim_id = created.json()["claim"]["id"]
    invalid = client.post(
        f"/api/v1/knowledge/claims/{claim_id}/transition",
        json={"lifecycle_status": "canonical"},
    )
    assert invalid.status_code == 409
