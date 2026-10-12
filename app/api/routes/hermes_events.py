from __future__ import annotations

import hashlib
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
from app.models.hermes_event import HermesEventReceipt
from app.schemas.hermes_events import HermesEventIn, HermesEventOut
from app.services.audit import record_audit

router = APIRouter(prefix="/hermes/events", tags=["hermes-events"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _fingerprint(payload: HermesEventIn) -> str:
    encoded = json.dumps(
        payload.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


@router.get("", response_model=list[HermesEventOut])
def list_hermes_events(
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
) -> list[HermesEventReceipt]:
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    statement = (
        select(HermesEventReceipt)
        .order_by(HermesEventReceipt.received_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement))


@router.post("", response_model=HermesEventOut, status_code=status.HTTP_201_CREATED)
def ingest_hermes_event(
    payload: HermesEventIn,
    db: DbSession,
    actor: Actor,
) -> HermesEventReceipt:
    authorize_mutation(
        db,
        actor,
        permission=AgentPermission.ingest_hermes_event,
        allow_human=False,
    )

    digest = _fingerprint(payload)
    existing = db.scalar(
        select(HermesEventReceipt).where(HermesEventReceipt.event_id == payload.event_id)
    )
    if existing is not None:
        if existing.payload_sha256 != digest:
            raise HTTPException(
                status_code=409,
                detail="event_id already exists with different envelope",
            )
        return existing

    receipt = HermesEventReceipt(
        event_id=payload.event_id,
        event_type=payload.event_type,
        producer=payload.producer,
        project_key=payload.project_id,
        schema_version=payload.schema_version,
        correlation_id=payload.correlation_id,
        causation_id=payload.causation_id,
        payload_sha256=digest,
        payload=payload.payload,
        metadata_json=payload.metadata,
        occurred_at=payload.timestamp,
    )
    db.add(receipt)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="hermes.event.received",
        entity_type="hermes_event",
        entity_id=payload.event_id,
        payload={
            "event_type": payload.event_type,
            "project_key": payload.project_id,
            "schema_version": payload.schema_version,
            "correlation_id": payload.correlation_id,
        },
    )
    db.commit()
    db.refresh(receipt)
    return receipt
