from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    request_id: str | None
    actor: str
    actor_type: str
    action: str
    entity_type: str
    entity_id: str
    payload: dict[str, object]
    created_at: datetime
