from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.core.config import settings


@dataclass(frozen=True)
class ActorContext:
    name: str
    actor_type: str


def get_actor(
    x_actor: str | None = Header(default=None, alias="X-Actor"),
    x_actor_type: str | None = Header(default=None, alias="X-Actor-Type"),
) -> ActorContext:
    if not x_actor:
        if settings.require_actor_header and settings.environment not in {"development", "test"}:
            raise HTTPException(status_code=401, detail="X-Actor header is required")
        x_actor = "local-user"
    return ActorContext(name=x_actor, actor_type=x_actor_type or "human")
