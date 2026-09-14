from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeClaim, KnowledgeLifecycle

GAP_SCAN_CANDIDATE_LIMIT = 500
LOW_CONFIDENCE_THRESHOLD = 60


def _is_expired(value: datetime | None, now: datetime) -> bool:
    if value is None:
        return False
    comparable = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return comparable < now


def find_knowledge_gaps(
    db: Session,
    *,
    namespace: str | None = None,
    project_id: UUID | None = None,
    limit: int = 100,
) -> list[KnowledgeClaim]:
    effective_limit = min(max(limit, 1), GAP_SCAN_CANDIDATE_LIMIT)
    statement = select(KnowledgeClaim).where(
        KnowledgeClaim.lifecycle_status != KnowledgeLifecycle.superseded.value
    )
    if namespace:
        statement = statement.where(KnowledgeClaim.namespace == namespace)
    if project_id is not None:
        statement = statement.where(KnowledgeClaim.project_id == project_id)
    statement = statement.order_by(
        KnowledgeClaim.confidence.asc(),
        KnowledgeClaim.updated_at.asc(),
    ).limit(GAP_SCAN_CANDIDATE_LIMIT)

    now = datetime.now(UTC)
    gaps: list[KnowledgeClaim] = []
    for claim in db.scalars(statement):
        if (
            claim.confidence < LOW_CONFIDENCE_THRESHOLD
            or not claim.evidence
            or _is_expired(claim.valid_until, now)
        ):
            gaps.append(claim)
            if len(gaps) >= effective_limit:
                break
    return gaps
