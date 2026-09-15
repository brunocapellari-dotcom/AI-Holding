from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge_source import (
    KnowledgeSource,
    SourceHealth,
    SourceStatus,
)
from app.schemas.knowledge_source import KnowledgeSourceCreate, KnowledgeSourceReview
from app.services.information_security import inspect_information, validate_public_source_uri
from app.services.safe_source_fetch import fetch_source


def create_source(db: Session, payload: KnowledgeSourceCreate) -> KnowledgeSource:
    validate_public_source_uri(payload.base_uri)
    validate_public_source_uri(payload.terms_uri)
    inspection = inspect_information(
        payload.name,
        payload.base_uri,
        payload.license_name,
        payload.terms_uri,
        payload.metadata_json,
    )
    if inspection.blocked:
        raise ValueError("source registration contains secret material")

    existing = db.scalar(select(KnowledgeSource).where(KnowledgeSource.key == payload.key))
    if existing is not None:
        raise ValueError("source key already exists")

    source = KnowledgeSource(
        key=payload.key,
        name=payload.name.strip(),
        base_uri=payload.base_uri.strip(),
        source_class=payload.source_class.value,
        status=SourceStatus.candidate.value,
        access_mode=payload.access_mode.value,
        trust_score=payload.trust_score,
        approved_for_fetch=False,
        license_name=payload.license_name,
        terms_uri=payload.terms_uri,
        expected_update_minutes=payload.expected_update_minutes,
        metadata_json={
            **payload.metadata_json,
            "security_flags": list(inspection.flags),
        },
    )
    db.add(source)
    db.flush()
    return source


def review_source(
    db: Session,
    source: KnowledgeSource,
    payload: KnowledgeSourceReview,
) -> KnowledgeSource:
    if payload.status == SourceStatus.approved and payload.trust_score is None:
        raise ValueError("approved sources require an explicit trust score")
    if payload.approved_for_fetch and source.access_mode != "public":
        raise ValueError("credentialed or manual sources cannot use automated fetch")

    source.status = payload.status.value
    source.approved_for_fetch = payload.approved_for_fetch
    if payload.trust_score is not None:
        source.trust_score = payload.trust_score
    if payload.license_name is not None:
        source.license_name = payload.license_name
    if payload.terms_uri is not None:
        validate_public_source_uri(payload.terms_uri)
        source.terms_uri = payload.terms_uri
    if payload.status in {SourceStatus.blocked, SourceStatus.rejected, SourceStatus.paused}:
        source.approved_for_fetch = False
    db.flush()
    return source


def check_source_health(
    db: Session,
    source: KnowledgeSource,
    *,
    transport: httpx.BaseTransport | None = None,
) -> tuple[SourceHealth, int | None, str | None, int]:
    checked_at = datetime.now(UTC)
    source.last_checked_at = checked_at
    try:
        result = fetch_source(source, transport=transport)
    except (httpx.HTTPError, ValueError):
        source.health_status = SourceHealth.unreachable.value
        db.flush()
        return SourceHealth.unreachable, None, None, 0

    source.last_success_at = checked_at
    source.health_status = SourceHealth.healthy.value
    metadata = dict(source.metadata_json or {})
    metadata["last_health"] = {
        "status_code": result.status_code,
        "content_type": result.content_type,
        "elapsed_ms": result.elapsed_ms,
        "checked_at": checked_at.isoformat(),
    }
    source.metadata_json = metadata
    db.flush()
    return (
        SourceHealth.healthy,
        result.status_code,
        result.content_type,
        result.elapsed_ms,
    )
