from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.core.config import settings
from app.db.session import get_db
from app.models.collector import Collector
from app.models.entities import Agent
from app.schemas.collectors import (
    CollectorActivation,
    CollectorCreate,
    CollectorOut,
    CollectorReport,
)
from app.services.audit import record_audit
from app.services.collectors import collector_is_stale, record_collection, set_collector_enabled

router = APIRouter(prefix="/collectors", tags=["collectors"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _collector_out(item: Collector) -> CollectorOut:
    return CollectorOut(
        id=item.id,
        collector_id=item.collector_id,
        source=item.source,
        collector_type=item.collector_type,
        frequency_seconds=item.frequency_seconds,
        last_collected_at=item.last_collected_at,
        last_success_at=item.last_success_at,
        status=item.status,
        latency_ms=item.latency_ms,
        failure_count=item.failure_count,
        consecutive_failures=item.consecutive_failures,
        owner_agent_id=item.owner_agent_id,
        produced_data=item.produced_data,
        last_error=item.last_error,
        metadata_json=item.metadata_json,
        stale=collector_is_stale(item),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _get_collector(db: Session, collector_id: UUID) -> Collector:
    collector = db.get(Collector, collector_id)
    if collector is None:
        raise HTTPException(status_code=404, detail="collector not found")
    return collector


@router.get("", response_model=list[CollectorOut])
def list_collectors(db: DbSession) -> list[CollectorOut]:
    items = db.scalars(select(Collector).order_by(Collector.collector_id)).all()
    return [_collector_out(item) for item in items]


@router.post("", response_model=CollectorOut, status_code=status.HTTP_201_CREATED)
def create_collector(
    payload: CollectorCreate,
    db: DbSession,
    actor: Actor,
) -> CollectorOut:
    authorize_mutation(db, actor)
    if payload.owner_agent_id is not None and db.get(Agent, payload.owner_agent_id) is None:
        raise HTTPException(status_code=404, detail="owner agent not found")

    collector = Collector(
        collector_id=payload.collector_id,
        source=payload.source,
        collector_type=payload.collector_type,
        frequency_seconds=payload.frequency_seconds,
        owner_agent_id=payload.owner_agent_id,
        produced_data=payload.produced_data,
        metadata_json=payload.metadata_json,
    )
    db.add(collector)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="collector_id already exists") from exc

    record_audit(
        db,
        actor=actor,
        action="collector.registered",
        entity_type="collector",
        entity_id=str(collector.id),
        payload={
            "collector_id": collector.collector_id,
            "source": collector.source,
            "collector_type": collector.collector_type,
            "owner_agent_id": str(collector.owner_agent_id) if collector.owner_agent_id else None,
        },
    )
    db.commit()
    db.refresh(collector)
    return _collector_out(collector)


@router.post("/{collector_id}/activation", response_model=CollectorOut)
def activate_collector(
    collector_id: UUID,
    payload: CollectorActivation,
    db: DbSession,
    actor: Actor,
) -> CollectorOut:
    authorize_mutation(db, actor)
    collector = _get_collector(db, collector_id)
    set_collector_enabled(collector, payload.enabled)
    record_audit(
        db,
        actor=actor,
        action="collector.activation_changed",
        entity_type="collector",
        entity_id=str(collector.id),
        payload={"enabled": payload.enabled, "status": collector.status},
    )
    db.commit()
    db.refresh(collector)
    return _collector_out(collector)


@router.post("/{collector_id}/report", response_model=CollectorOut)
def report_collection(
    collector_id: UUID,
    payload: CollectorReport,
    db: DbSession,
    actor: Actor,
) -> CollectorOut:
    collector = _get_collector(db, collector_id)
    if settings.environment == "production" and collector.owner_agent_id is None:
        raise HTTPException(status_code=409, detail="collector has no canonical owner agent")

    authorize_mutation(
        db,
        actor,
        permission=AgentPermission.report_collection,
        expected_agent_id=collector.owner_agent_id,
        allow_human=False,
    )
    try:
        record_collection(collector, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    record_audit(
        db,
        actor=actor,
        action="collector.collection_reported",
        entity_type="collector",
        entity_id=str(collector.id),
        payload={
            "success": payload.success,
            "latency_ms": payload.latency_ms,
            "status": collector.status,
            "failure_count": collector.failure_count,
            "consecutive_failures": collector.consecutive_failures,
        },
    )
    db.commit()
    db.refresh(collector)
    return _collector_out(collector)
