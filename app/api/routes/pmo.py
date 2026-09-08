from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
from app.models.entities import Agent, AgentStatus
from app.schemas.operations import TaskClaimOut, TaskClaimRequest
from app.services.pmo import claim_next_task

router = APIRouter(prefix="/pmo", tags=["pmo"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


@router.post(
    "/claim",
    response_model=TaskClaimOut,
    responses={204: {"description": "No eligible work available"}},
)
def claim_work(
    payload: TaskClaimRequest,
    db: DbSession,
    actor: Actor,
) -> TaskClaimOut | Response:
    agent = db.get(Agent, payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    if agent.status != AgentStatus.active:
        raise HTTPException(status_code=409, detail="only active agents can claim work")

    authorize_mutation(
        db,
        actor,
        permission=AgentPermission.claim_work,
        expected_agent_id=agent.id,
        allow_human=False,
    )

    execution_kinds = tuple(item.value for item in payload.execution_kinds)
    try:
        claimed = claim_next_task(
            db,
            agent=agent,
            actor=actor,
            execution_kinds=execution_kinds,
            project_id=payload.project_id,
        )
        if claimed is None:
            db.rollback()
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        task, run = claimed
        db.commit()
        db.refresh(task)
        db.refresh(run)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="claim conflict; retry") from exc

    return TaskClaimOut.model_validate(
        {"task": task, "run": run},
        from_attributes=True,
    )
