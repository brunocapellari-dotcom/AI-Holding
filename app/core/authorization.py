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
from app.models.human_identity import HumanIdentityRole, HumanRole

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
            AgentPermission.claim_work,
            AgentPermission.transition_own_task,
            AgentPermission.transition_own_run,
            AgentPermission.create_incident,
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


def _bound_human_role(db: Session, actor: ActorContext) -> HumanRole:
    if (
        not actor.authenticated
        or actor.actor_type != "human"
        or not actor.issuer
        or not actor.subject
    ):
        raise _forbidden("authenticated human identity is required")

    binding = db.scalar(
        select(HumanIdentityRole).where(
            HumanIdentityRole.issuer == actor.issuer,
            HumanIdentityRole.subject == actor.subject,
        )
    )
    if binding is None:
        logger.warning("unbound human attempted a mutation")
        raise _forbidden("human identity is not bound to an authorized role")
    if binding.email.casefold() != actor.name.casefold():
        logger.warning("human identity email drift detected for bound subject")
        raise _forbidden("human identity binding does not match the verified email")

    try:
        return HumanRole(binding.role)
    except ValueError as exc:
        logger.error("human identity binding contains an invalid role")
        raise _forbidden("human identity binding is invalid") from exc


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
    human mutations require an explicit subject-bound owner role in addition to the
    Cloud Run IAM invoker boundary. Other human roles are read-only until a granular
    permission matrix is explicitly introduced. Service accounts are denied by
    default and require a canonical binding plus an explicit code-owned permission.
    """

    if settings.environment in {"development", "test"}:
        return None

    if not actor.authenticated:
        raise _forbidden("authenticated identity is required")

    if actor.actor_type == "human":
        if not allow_human:
            raise _forbidden("this mutation requires a canonical service agent")
        human_role = _bound_human_role(db, actor)
        if human_role != HumanRole.owner:
            raise _forbidden(
                f"human role {human_role.value} is read-only for mutations"
            )
        return None

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
