from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models.knowledge import (
    EpistemicStatus,
    KnowledgeClaim,
    KnowledgeLifecycle,
    KnowledgeOutcome,
)

OUTCOME_REVIEW_CANDIDATE_LIMIT = 500
REVIEWABLE_EPISTEMIC_STATUSES = (
    EpistemicStatus.estimated.value,
    EpistemicStatus.projected.value,
    EpistemicStatus.inferred.value,
)
REVIEWABLE_LIFECYCLES = (
    KnowledgeLifecycle.validated.value,
    KnowledgeLifecycle.canonical.value,
)


def find_outcome_review_candidates(
    db: Session,
    *,
    namespace: str | None = None,
    project_id: UUID | None = None,
    limit: int = 100,
) -> list[KnowledgeClaim]:
    effective_limit = min(max(limit, 1), OUTCOME_REVIEW_CANDIDATE_LIMIT)
    now = datetime.now(UTC)
    has_outcome = exists(select(1).where(KnowledgeOutcome.claim_id == KnowledgeClaim.id))
    statement = select(KnowledgeClaim).where(
        KnowledgeClaim.lifecycle_status.in_(REVIEWABLE_LIFECYCLES),
        KnowledgeClaim.epistemic_status.in_(REVIEWABLE_EPISTEMIC_STATUSES),
        KnowledgeClaim.valid_until.is_not(None),
        KnowledgeClaim.valid_until <= now,
        ~has_outcome,
    )
    if namespace:
        statement = statement.where(KnowledgeClaim.namespace == namespace)
    if project_id is not None:
        statement = statement.where(KnowledgeClaim.project_id == project_id)
    statement = statement.order_by(
        KnowledgeClaim.valid_until.asc(),
        KnowledgeClaim.updated_at.asc(),
    ).limit(effective_limit)
    return list(db.scalars(statement))
