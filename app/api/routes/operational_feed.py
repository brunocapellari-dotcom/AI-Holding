"""Read-only sanitized Hermes activity feed for the owner console.

The feed reports RECEIVED event evidence, not project availability or go-live status.
Never expose raw event payload, metadata, secrets, or project-internal data in the UI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import ReadScope, authorize_read
from app.db.session import get_db
from app.models.hermes_event import HermesEventReceipt

router = APIRouter(prefix="/holding/control-plane", tags=["operational-feed"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@router.get("/event-feed")
def operational_event_feed(
    db: DbSession,
    actor: Actor,
    limit: int = Query(default=30, ge=1, le=100),
    project_key: str | None = Query(default=None, min_length=1, max_length=120),
) -> dict[str, object]:
    """Describe persisted Hermes activity, without interpreting it as service health."""
    authorize_read(db, actor, scope=ReadScope.governance)
    stmt = select(HermesEventReceipt).order_by(
        HermesEventReceipt.received_at.desc(), HermesEventReceipt.id.desc()
    )
    if project_key is not None:
        stmt = stmt.where(HermesEventReceipt.project_key == project_key)
    records = list(db.scalars(stmt.limit(limit)))
    now = datetime.now(UTC)
    events: list[dict[str, object]] = []
    for receipt in records:
        received = _utc(receipt.received_at)
        occurred = _utc(receipt.occurred_at)
        age_seconds = max(0, int((now - received).total_seconds()))
        events.append({
            "event_id": receipt.event_id,
            "event_type": receipt.event_type,
            "project_key": receipt.project_key,
            "producer": receipt.producer,
            "occurred_at": occurred.isoformat(),
            "received_at": received.isoformat(),
            "received_age_seconds": age_seconds,
        })
    return {
        "generated_at": now.isoformat(),
        "kind": "recorded_hermes_activity",
        "availability_verified": False,
        "items": events,
    }
