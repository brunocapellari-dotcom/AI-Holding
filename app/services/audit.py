from sqlalchemy.orm import Session

from app.core.actor import ActorContext
from app.core.request_context import request_id_ctx
from app.models.entities import AuditEvent


def record_audit(
    db: Session,
    *,
    actor: ActorContext,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            request_id=request_id_ctx.get(),
            actor=actor.name,
            actor_type=actor.actor_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )
