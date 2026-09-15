from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
from app.models.knowledge_source import KnowledgeSource, SourceStatus
from app.schemas.knowledge_source import (
    KnowledgeSourceCreate,
    KnowledgeSourceHealthOut,
    KnowledgeSourceOut,
    KnowledgeSourceReview,
)
from app.services.audit import record_audit
from app.services.knowledge_source import check_source_health, create_source, review_source

router = APIRouter(prefix="/knowledge/sources", tags=["knowledge-sources"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _source_or_404(db: Session, source_id: UUID) -> KnowledgeSource:
    source = db.get(KnowledgeSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="knowledge source not found")
    return source


@router.get("", response_model=list[KnowledgeSourceOut])
def list_sources(
    db: DbSession,
    status_filter: SourceStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[KnowledgeSource]:
    statement = select(KnowledgeSource)
    if status_filter is not None:
        statement = statement.where(KnowledgeSource.status == status_filter.value)
    statement = statement.order_by(KnowledgeSource.updated_at.desc())
    statement = statement.limit(min(max(limit, 1), 500)).offset(max(offset, 0))
    return list(db.scalars(statement))


@router.get("/{source_id}", response_model=KnowledgeSourceOut)
def get_source(source_id: UUID, db: DbSession) -> KnowledgeSource:
    return _source_or_404(db, source_id)


@router.post("", response_model=KnowledgeSourceOut, status_code=status.HTTP_201_CREATED)
def register_source(
    payload: KnowledgeSourceCreate,
    db: DbSession,
    actor: Actor,
) -> KnowledgeSource:
    authorize_mutation(
        db,
        actor,
        permission=AgentPermission.submit_source_candidate,
    )
    try:
        source = create_source(db, payload)
        record_audit(
            db,
            actor=actor,
            action="knowledge_source.registered",
            entity_type="knowledge_source",
            entity_id=str(source.id),
            payload={
                "key": source.key,
                "source_class": source.source_class,
                "status": source.status,
            },
        )
        db.commit()
        db.refresh(source)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="source conflicts with stored state") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return source


@router.post("/{source_id}/review", response_model=KnowledgeSourceOut)
def review_registered_source(
    source_id: UUID,
    payload: KnowledgeSourceReview,
    db: DbSession,
    actor: Actor,
) -> KnowledgeSource:
    authorize_mutation(db, actor, permission=AgentPermission.review_source)
    source = _source_or_404(db, source_id)
    previous = source.status
    try:
        review_source(db, source, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit(
        db,
        actor=actor,
        action="knowledge_source.reviewed",
        entity_type="knowledge_source",
        entity_id=str(source.id),
        payload={
            "from": previous,
            "to": source.status,
            "approved_for_fetch": source.approved_for_fetch,
            "trust_score": source.trust_score,
        },
    )
    db.commit()
    db.refresh(source)
    return source


@router.post("/{source_id}/health", response_model=KnowledgeSourceHealthOut)
def source_health_check(
    source_id: UUID,
    db: DbSession,
    actor: Actor,
) -> KnowledgeSourceHealthOut:
    authorize_mutation(db, actor, permission=AgentPermission.check_source_health)
    source = _source_or_404(db, source_id)
    checked_at = datetime.now(UTC)
    health, status_code, content_type, elapsed_ms = check_source_health(db, source)
    record_audit(
        db,
        actor=actor,
        action="knowledge_source.health_checked",
        entity_type="knowledge_source",
        entity_id=str(source.id),
        payload={
            "health_status": health.value,
            "status_code": status_code,
            "content_type": content_type,
            "elapsed_ms": elapsed_ms,
        },
    )
    db.commit()
    return KnowledgeSourceHealthOut(
        source_id=source.id,
        health_status=health,
        status_code=status_code,
        content_type=content_type,
        checked_at=checked_at,
        elapsed_ms=elapsed_ms,
    )
