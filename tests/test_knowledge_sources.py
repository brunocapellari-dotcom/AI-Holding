from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.models.knowledge_source import KnowledgeSource
from app.services import safe_source_fetch


def _source_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "key": "USDA_PUBLIC",
        "name": "USDA public source",
        "base_uri": "https://example.com/data",
        "source_class": "primary",
        "access_mode": "public",
        "trust_score": 90,
        "license_name": "public-data",
        "terms_uri": "https://example.com/terms",
        "expected_update_minutes": 1440,
    }
    payload.update(overrides)
    return payload


def test_source_registration_starts_candidate_and_requires_review(client: TestClient) -> None:
    created = client.post("/api/v1/knowledge/sources", json=_source_payload())
    assert created.status_code == 201
    source = created.json()
    assert source["status"] == "candidate"
    assert source["approved_for_fetch"] is False
    assert source["trust_score"] == 90

    invalid = client.post(
        f"/api/v1/knowledge/sources/{source['id']}/review",
        json={"status": "candidate", "approved_for_fetch": True, "trust_score": 90},
    )
    assert invalid.status_code == 422

    approved = client.post(
        f"/api/v1/knowledge/sources/{source['id']}/review",
        json={"status": "approved", "approved_for_fetch": True, "trust_score": 95},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_for_fetch"] is True
    assert approved.json()["trust_score"] == 95


def test_credentialed_source_cannot_be_enabled_for_automatic_fetch(client: TestClient) -> None:
    created = client.post(
        "/api/v1/knowledge/sources",
        json=_source_payload(key="AUTHORIZED_ONLY", access_mode="authorized"),
    )
    assert created.status_code == 201

    reviewed = client.post(
        f"/api/v1/knowledge/sources/{created.json()['id']}/review",
        json={"status": "approved", "approved_for_fetch": True, "trust_score": 80},
    )
    assert reviewed.status_code == 409


def test_source_registry_rejects_sensitive_uri_query(client: TestClient) -> None:
    sensitive_key = "to" + "ken"
    payload = _source_payload(
        key="UNSAFE_URI",
        base_uri="https://example.com/data?" + sensitive_key + "=synthetic-value",
    )
    response = client.post("/api/v1/knowledge/sources", json=payload)
    assert response.status_code == 400


def test_safe_fetch_rejects_nonpublic_network(monkeypatch: pytest.MonkeyPatch) -> None:
    source = KnowledgeSource(
        key="PRIVATE_NET",
        name="Private network",
        base_uri="https://127.0.0.1/data",
        source_class="primary",
        status="approved",
        health_status="unknown",
        access_mode="public",
        trust_score=100,
        approved_for_fetch=True,
    )
    with pytest.raises(ValueError, match="non-public"):
        safe_source_fetch.fetch_source(source)


def test_safe_fetch_is_bounded_to_approved_domain_and_content_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(safe_source_fetch, "_assert_public_host", lambda hostname: None)
    source = KnowledgeSource(
        key="PUBLIC",
        name="Public source",
        base_uri="https://example.com/data",
        source_class="primary",
        status="approved",
        health_status="unknown",
        access_mode="public",
        trust_score=100,
        approved_for_fetch=True,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b'{"ok":true}',
            request=request,
        )

    result = safe_source_fetch.fetch_source(
        source,
        transport=httpx.MockTransport(handler),
    )
    assert result.status_code == 200
    assert result.content_type == "application/json"
    assert result.content == b'{"ok":true}'

    with pytest.raises(ValueError, match="approved source domain"):
        safe_source_fetch.fetch_source(
            source,
            relative_or_absolute_url="https://attacker.invalid/data",
            transport=httpx.MockTransport(handler),
        )


def test_safe_fetch_rejects_disallowed_content_and_oversized_declared_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(safe_source_fetch, "_assert_public_host", lambda hostname: None)
    source = KnowledgeSource(
        key="PUBLIC2",
        name="Public source 2",
        base_uri="https://example.com/data",
        source_class="primary",
        status="approved",
        health_status="unknown",
        access_mode="public",
        trust_score=100,
        approved_for_fetch=True,
    )

    def html_binary(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/octet-stream"},
            content=b"abc",
            request=request,
        )

    with pytest.raises(ValueError, match="disallowed content type"):
        safe_source_fetch.fetch_source(source, transport=httpx.MockTransport(html_binary))

    def oversized(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/plain",
                "content-length": str(safe_source_fetch.MAX_SOURCE_BYTES + 1),
            },
            content=b"small",
            request=request,
        )

    with pytest.raises(ValueError, match="maximum allowed size"):
        safe_source_fetch.fetch_source(source, transport=httpx.MockTransport(oversized))
