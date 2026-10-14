from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import authorize_mutation
from app.db.session import get_db
from app.models.entities import Agent, AgentStatus
from app.schemas.operations import AgentCreate, AgentOut, AgentTransition
from app.services.audit import record_audit

router = APIRouter(prefix="/agents", tags=["agents"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]

ALLOWED_TRANSITIONS: dict[AgentStatus, set[AgentStatus]] = {
    AgentStatus.active: {AgentStatus.degraded, AgentStatus.disabled},
    AgentStatus.degraded: {AgentStatus.active, AgentStatus.disabled},
    AgentStatus.disabled: {AgentStatus.active},
}


@router.get("", response_model=list[AgentOut])
def list_agents(db: DbSession, limit: int = 100, offset: int = 0) -> list[Agent]:
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    statement = select(Agent).order_by(Agent.name).limit(limit).offset(offset)
    return list(db.scalars(statement))


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, db: DbSession, actor: Actor) -> Agent:
    authorize_mutation(db, actor)

    capabilities = list(dict.fromkeys(payload.capabilities))
    agent = Agent(
        key=payload.key,
        name=payload.name,
        role=payload.role,
        max_autonomy=payload.max_autonomy,
        model_policy=payload.model_policy,
        capabilities=cast(list[object], capabilities),
    )
    db.add(agent)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="agent key already exists") from exc

    record_audit(
        db,
        actor=actor,
        action="agent.created",
        entity_type="agent",
        entity_id=str(agent.id),
        payload={"max_autonomy": agent.max_autonomy, "capabilities": len(capabilities)},
    )
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/{agent_id}/transition", response_model=AgentOut)
def transition_agent(
    agent_id: UUID,
    payload: AgentTransition,
    db: DbSession,
    actor: Actor,
) -> Agent:
    authorize_mutation(db, actor)

    agent = db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
    if payload.status not in ALLOWED_TRANSITIONS[agent.status]:
        raise HTTPException(
            status_code=409,
            detail=f"invalid transition {agent.status.value} -> {payload.status.value}",
        )

    old_status = agent.status
    agent.status = payload.status
    record_audit(
        db,
        actor=actor,
        action="agent.transitioned",
        entity_type="agent",
        entity_id=str(agent.id),
        payload={"from": old_status.value, "to": agent.status.value},
    )
    db.commit()
    db.refresh(agent)
    return agent
