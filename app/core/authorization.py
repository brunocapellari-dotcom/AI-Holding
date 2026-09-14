from __future__ import annotations

import logging
from enum import StrEnum
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus

logger = logging.getLogger("holding-control-plane.authorization")


class AgentPermission(StrEnum):
    claim_work = "claim_work"
    transition_own_task = "transition_own_task"
    transition_own_run = "transition_own_run"
    evaluate_own_policy = "evaluate_own_policy"
    create_incident = "create_incident"
    submit_knowledge = "submit_knowledge"
    promote_knowledge = "promote_knowledge"
    submit_knowledge_outcome = "submit_knowledge_outcome"
    export_knowledge = "export_knowledge"


AGENT_PERMISSIONS: dict[str, frozenset[AgentPermission]] = {
    "PMO_IA": frozenset(
        {
            AgentPermission.claim_work,
            AgentPermission.transition_own_task,
            AgentPermission.transition_own_run,
            AgentPermission.evaluate_own_policy,
            AgentPermission.create_incident,
        }
    ),
    "KNOWLEDGE_IA": frozenset(
        {
            AgentPermission.submit_knowledge,
            AgentPermission.submit_knowledge_outcome,
            AgentPermission.export_knowledge,
        }
    ),
    "AUDITOR_IA": frozenset(
        {
            AgentPermission.promote_knowledge,
            AgentPermission.submit_knowledge_outcome,
            AgentPermission.export_knowledge,
        }
    ),
}


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=403, detail=detail)


def _bound_agent(db: Session, actor: ActorContext) -> Agent:
    if (
        not actor.authenticated
        or actor.actor_type != "service-account"
        or not actor.issuer
        or not actor.subject
    ):
        raise _forbidden("authenticated service-account identity is required")

    identity = db.scalar(
        select(AgentIdentity).where(
            AgentIdentity.issuer == actor.issuer,
            AgentIdentity.subject == actor.subject,
        )
    )
    if identity is None:
        logger.warning("unbound service-account attempted an agent action")
        raise _forbidden("service-account is not bound to a canonical agent")

    agent = db.get(Agent, identity.agent_id)
    if agent is None:
        logger.error("agent identity points to a missing canonical agent")
        raise _forbidden("canonical agent binding is invalid")
    if agent.status != AgentStatus.active:
        raise _forbidden("canonical agent is not active")
    return agent


def authorize_mutation(
    db: Session,
    actor: ActorContext,
    *,
    permission: AgentPermission | None = None,
    expected_agent_id: UUID | None = None,
    allow_human: bool = True,
) -> Agent | None:
    """Authorize a write operation and return the bound service agent when applicable.

    Development and test environments preserve local ergonomics. In production,
    authenticated humans are governed by the Cloud Run IAM invoker boundary when
    the route explicitly permits human operation. Service accounts are denied by
    default and require a canonical binding plus an explicit code-owned permission.
    """

    if settings.environment in {"development", "test"}:
        return None

    if not actor.authenticated:
        raise _forbidden("authenticated identity is required")

    if actor.actor_type == "human":
        if allow_human:
            return None
        raise _forbidden("this mutation requires a canonical service agent")

    if actor.actor_type != "service-account":
        raise _forbidden("actor type is not authorized for mutations")

    if permission is None:
        raise _forbidden("service-account is not authorized for this mutation")

    agent = _bound_agent(db, actor)
    allowed = AGENT_PERMISSIONS.get(agent.key, frozenset())
    if permission not in allowed:
        raise _forbidden("canonical agent does not have this permission")
    if expected_agent_id is not None and agent.id != expected_agent_id:
        raise _forbidden("service-account cannot act as another agent")
    return agent
