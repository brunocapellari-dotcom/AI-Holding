from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.knowledge_gap import find_knowledge_gaps


def _ingest(
    client: TestClient,
    *,
    statement: str,
    confidence: int,
    evidence: list[dict[str, object]],
    valid_until: datetime | None = None,
) -> None:
    payload: dict[str, object] = {
        "namespace": "shared",
        "statement": statement,
        "confidence": confidence,
        "source_name": "gap-test",
        "evidence": evidence,
    }
    if valid_until is not None:
        payload["valid_until"] = valid_until.isoformat()
    response = client.post("/api/v1/knowledge/claims", json=payload)
    assert response.status_code == 201, response.text


def test_gap_scan_finds_low_confidence_missing_evidence_and_expired_claims(
    client: TestClient,
    db_session: Session,
) -> None:
    evidence = [{"source": "test-source", "locator": "record-1"}]
    _ingest(
        client,
        statement="Strong current claim has enough evidence and confidence.",
        confidence=90,
        evidence=evidence,
    )
    _ingest(
        client,
        statement="Low confidence claim needs additional validation.",
        confidence=40,
        evidence=evidence,
    )
    _ingest(
        client,
        statement="Claim without evidence needs source support.",
        confidence=90,
        evidence=[],
    )
    _ingest(
        client,
        statement="Expired claim needs a freshness review.",
        confidence=90,
        evidence=evidence,
        valid_until=datetime.now(UTC) - timedelta(days=1),
    )

    gaps = find_knowledge_gaps(db_session, namespace="shared")
    statements = {claim.statement for claim in gaps}
    assert statements == {
        "Low confidence claim needs additional validation.",
        "Claim without evidence needs source support.",
        "Expired claim needs a freshness review.",
    }


def test_gap_scan_honors_result_limit(client: TestClient, db_session: Session) -> None:
    for index in range(3):
        _ingest(
            client,
            statement=f"Gap candidate number {index} requires validation.",
            confidence=10 + index,
            evidence=[],
        )

    gaps = find_knowledge_gaps(db_session, namespace="shared", limit=2)
    assert len(gaps) == 2
