from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeClaim, KnowledgeLifecycle


def find_knowledge_gaps(
    db: Session,
    *,
    namespace: str | None = None,
    project_id: UUID | None = None,
    limit: int = 100,
) -> list[KnowledgeClaim]:
    now = datetime.now(UTC)
    statement = select(KnowledgeClaim).where(
        KnowledgeClaim.lifecycle_status != KnowledgeLifecycle.superseded.value,
        or_(
            KnowledgeClaim.valid_until < now,
            KnowledgeClaim.confidence < 0.6,
            KnowledgeClaim.evidence == [],
        ),
    )
    if namespace:
        statement = statement.where(KnowledgeClaim.namespace == namespace)
    if project_id is not None:
        statement = statement.where(KnowledgeClaim.project_id == project_id)
    statement = statement.order_by(
        KnowledgeClaim.confidence.asc(),
        KnowledgeClaim.updated_at.asc(),
    ).limit(min(max(limit, 1), 500))
    return list(db.scalars(statement))
