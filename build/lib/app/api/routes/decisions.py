from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import authorize_mutation
from app.db.session import get_db
from app.models.entities import Approval, Decision, DecisionStatus, Project
from app.schemas.api import DecisionCreate, DecisionOut, DecisionResolve
from app.services.audit import record_audit

router = APIRouter(prefix="/decisions", tags=["decisions"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


@router.get("/pending-human", response_model=list[DecisionOut])
def pending_human_decisions(db: DbSession) -> list[Decision]:
    stmt = (
        select(Decision)
        .where(
            Decision.status == DecisionStatus.pending,
            Decision.requires_human.is_(True),
        )
        .order_by(Decision.created_at)
    )
    return list(db.scalars(stmt))


@router.post("", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def create_decision(
    payload: DecisionCreate,
    db: DbSession,
    actor: Actor,
) -> Decision:
    authorize_mutation(db, actor)

    if not db.get(Project, payload.project_id):
        raise HTTPException(status_code=404, detail="project not found")
    decision = Decision(**payload.model_dump())
    db.add(decision)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="decision key already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="decision.created",
        entity_type="decision",
        entity_id=str(decision.id),
        payload={"requires_human": decision.requires_human},
    )
    db.commit()
    db.refresh(decision)
    return decision


@router.post("/{decision_id}/resolve", response_model=DecisionOut)
def resolve_decision(
    decision_id: UUID,
    payload: DecisionResolve,
    db: DbSession,
    actor: Actor,
) -> Decision:
    authorize_mutation(db, actor)

    decision = db.get(Decision, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="decision not found")
    if decision.status != DecisionStatus.pending:
        raise HTTPException(status_code=409, detail="decision already resolved")
    if payload.outcome not in {DecisionStatus.approved, DecisionStatus.rejected}:
        raise HTTPException(status_code=422, detail="outcome must be approved or rejected")

    decision.status = payload.outcome
    decision.resolution = {"actor": actor.name, "rationale": payload.rationale}
    db.add(
        Approval(
            decision_id=decision.id,
            actor=actor.name,
            outcome=payload.outcome,
            rationale=payload.rationale,
        )
    )
    record_audit(
        db,
        actor=actor,
        action="decision.resolved",
        entity_type="decision",
        entity_id=str(decision.id),
        payload={"outcome": payload.outcome.value},
    )
    db.commit()
    db.refresh(decision)
    return decision
