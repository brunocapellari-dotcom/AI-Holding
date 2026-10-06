from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access_dependencies import require_audit_read
from app.db.session import get_db
from app.models.entities import AuditEvent
from app.schemas.audit import AuditEventOut

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(require_audit_read)],
)
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/events", response_model=list[AuditEventOut])
def list_audit_events(
    db: DbSession,
    actor: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    request_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEvent]:
    effective_limit = min(max(limit, 1), 200)
    effective_offset = min(max(offset, 0), 10_000)

    statement = select(AuditEvent)
    if actor:
        statement = statement.where(AuditEvent.actor == actor.strip())
    if action:
        statement = statement.where(AuditEvent.action == action.strip())
    if entity_type:
        statement = statement.where(AuditEvent.entity_type == entity_type.strip())
    if entity_id:
        statement = statement.where(AuditEvent.entity_id == entity_id.strip())
    if request_id:
        statement = statement.where(AuditEvent.request_id == request_id.strip())

    statement = (
        statement.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(effective_limit)
        .offset(effective_offset)
    )
    return list(db.scalars(statement))
