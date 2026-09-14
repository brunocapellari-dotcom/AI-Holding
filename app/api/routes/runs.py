from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
from app.models.entities import Agent, AgentStatus, Run, RunStatus, Task, WorkStatus
from app.schemas.operations import RunCreate, RunOut, RunTransition
from app.services.audit import record_audit
from app.services.knowledge_autonomy import capture_run_learning

router = APIRouter(prefix="/runs", tags=["runs"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]

ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.queued: {RunStatus.running, RunStatus.cancelled},
    RunStatus.running: {RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled},
    RunStatus.succeeded: set(),
    RunStatus.failed: set(),
    RunStatus.cancelled: set(),
}
ACTIVE_STATUSES = {RunStatus.queued, RunStatus.running}
TERMINAL_STATUSES = {RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled}


@router.get("", response_model=list[RunOut])
def list_runs(
    db: DbSession,
    task_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Run]:
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    statement = select(Run)
    if task_id:
        statement = statement.where(Run.task_id == task_id)
    statement = statement.order_by(Run.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement))


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, db: DbSession, actor: Actor) -> Run:
    authorize_mutation(db, actor)

    task = db.get(Task, payload.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status != WorkStatus.running:
        raise HTTPException(status_code=409, detail="task must be running before execution starts")

    if payload.external_run_id:
        existing = db.scalar(select(Run).where(Run.external_run_id == payload.external_run_id))
        if existing:
            return existing

    if payload.agent_id:
        agent = db.get(Agent, payload.agent_id)
        if not agent:
            raise HTTPException(status_code=400, detail="agent not found")
        if agent.status == AgentStatus.disabled:
            raise HTTPException(status_code=409, detail="disabled agent cannot execute work")

    active = db.scalar(
        select(Run).where(Run.task_id == task.id, Run.status.in_(ACTIVE_STATUSES)).limit(1)
    )
    if active:
        raise HTTPException(status_code=409, detail="task already has an active run")

    last_attempt = db.scalar(select(func.max(Run.attempt)).where(Run.task_id == task.id)) or 0
    run = Run(
        task_id=task.id,
        agent_id=payload.agent_id,
        attempt=last_attempt + 1,
        external_run_id=payload.external_run_id,
        input_metadata=payload.input_metadata,
    )
    db.add(run)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="external run id already exists") from exc

    record_audit(
        db,
        actor=actor,
        action="run.created",
        entity_type="run",
        entity_id=str(run.id),
        payload={"task_id": str(task.id), "attempt": run.attempt},
    )
    db.commit()
    db.refresh(run)
    return run


@router.post("/{run_id}/transition", response_model=RunOut)
def transition_run(
    run_id: UUID,
    payload: RunTransition,
    db: DbSession,
    actor: Actor,
) -> Run:
    bound_agent = authorize_mutation(
        db,
        actor,
        permission=AgentPermission.transition_own_run,
    )

    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if bound_agent is not None and run.agent_id != bound_agent.id:
        raise HTTPException(status_code=403, detail="agent can only transition its own run")
    if payload.status not in ALLOWED_TRANSITIONS[run.status]:
        raise HTTPException(
            status_code=409,
            detail=f"invalid transition {run.status.value} -> {payload.status.value}",
        )

    now = datetime.now(UTC)
    old_status = run.status
    run.status = payload.status
    if payload.status == RunStatus.running:
        run.started_at = now
    if payload.status in TERMINAL_STATUSES:
        run.finished_at = now
        run.output_metadata = payload.output_metadata
        run.error = payload.error

    if payload.status == RunStatus.succeeded:
        task = db.get(Task, run.task_id)
        if task is not None:
            knowledge_claim_ids: list[UUID] = []
            capture_failed = False
            try:
                with db.begin_nested():
                    knowledge_claim_ids = capture_run_learning(
                        db,
                        run=run,
                        task=task,
                        actor_agent_id=(bound_agent.id if bound_agent is not None else run.agent_id),
                    )
            except SQLAlchemyError:
                capture_failed = True

            output_metadata = dict(run.output_metadata or {})
            output_metadata["knowledge_capture"] = {
                "status": "failed" if capture_failed else "captured",
                "created_claims": len(knowledge_claim_ids),
            }
            run.output_metadata = output_metadata
            if knowledge_claim_ids:
                record_audit(
                    db,
                    actor=actor,
                    action="run.knowledge_captured",
                    entity_type="run",
                    entity_id=str(run.id),
                    payload={
                        "task_id": str(task.id),
                        "knowledge_claim_ids": [str(item) for item in knowledge_claim_ids],
                    },
                )

    record_audit(
        db,
        actor=actor,
        action="run.transitioned",
        entity_type="run",
        entity_id=str(run.id),
        payload={"from": old_status.value, "to": run.status.value},
    )
    db.commit()
    db.refresh(run)
    return run
