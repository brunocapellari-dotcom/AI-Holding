from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
from app.models.entities import Milestone, Project, ProjectStatus, Task, TaskDependency, WorkStatus
from app.models.control_plane import ReleaseRecord
from app.schemas.api import TaskCreate, TaskOut, TaskTransition
from app.services.audit import record_audit
from app.services.control_plane import task_done_reasons, wip_count

router = APIRouter(prefix="/tasks", tags=["tasks"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]

ALLOWED_TRANSITIONS: dict[WorkStatus, set[WorkStatus]] = {
    WorkStatus.planned: {WorkStatus.ready, WorkStatus.cancelled},
    WorkStatus.ready: {WorkStatus.running, WorkStatus.blocked, WorkStatus.cancelled},
    WorkStatus.running: {WorkStatus.review, WorkStatus.blocked, WorkStatus.cancelled},
    WorkStatus.blocked: {WorkStatus.ready, WorkStatus.cancelled},
    WorkStatus.review: {WorkStatus.running, WorkStatus.testing, WorkStatus.done, WorkStatus.blocked},
    WorkStatus.testing: {WorkStatus.running, WorkStatus.done, WorkStatus.blocked},
    WorkStatus.done: set(),
    WorkStatus.cancelled: set(),
}
SERVICE_AGENT_TRANSITIONS = {WorkStatus.review, WorkStatus.blocked}


@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
) -> list[Task]:
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    statement = select(Task).order_by(Task.priority, Task.created_at).limit(limit).offset(offset)
    return list(db.scalars(statement))


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: DbSession,
    actor: Actor,
) -> Task:
    authorize_mutation(db, actor)

    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if project.status in {ProjectStatus.paused, ProjectStatus.archived, ProjectStatus.discontinued}:
        raise HTTPException(status_code=409, detail="project is not accepting new executable work")
    if payload.milestone_id:
        milestone = db.get(Milestone, payload.milestone_id)
        if not milestone or milestone.project_id != project.id:
            raise HTTPException(status_code=400, detail="milestone does not belong to project")
    if payload.release_id:
        release = db.get(ReleaseRecord, payload.release_id)
        if not release or release.project_id != project.id:
            raise HTTPException(status_code=400, detail="release does not belong to project")

    existing = db.scalar(select(Task).where(Task.idempotency_key == payload.idempotency_key))
    if existing:
        return existing

    dependency_ids = list(dict.fromkeys(payload.depends_on))
    for dependency_id in dependency_ids:
        dependency = db.get(Task, dependency_id)
        if not dependency or dependency.project_id != project.id:
            raise HTTPException(
                status_code=400,
                detail="invalid cross-project or missing dependency",
            )

    data = payload.model_dump(exclude={"depends_on"})
    task = Task(**data)
    db.add(task)
    try:
        db.flush()
        for dependency_id in dependency_ids:
            db.add(TaskDependency(task_id=task.id, depends_on_task_id=dependency_id))
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="task key or idempotency key already exists",
        ) from exc

    record_audit(
        db,
        actor=actor,
        action="task.created",
        entity_type="task",
        entity_id=str(task.id),
        payload={
            "project_id": str(task.project_id),
            "dependencies": len(dependency_ids),
            "execution_kind": task.execution_kind,
            "auto_start": task.auto_start,
        },
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/transition", response_model=TaskOut)
def transition_task(
    task_id: UUID,
    payload: TaskTransition,
    db: DbSession,
    actor: Actor,
) -> Task:
    bound_agent = authorize_mutation(
        db,
        actor,
        permission=AgentPermission.transition_own_task,
    )

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if bound_agent is not None:
        if task.assigned_agent_id != bound_agent.id:
            raise HTTPException(
                status_code=403,
                detail="agent can only transition its assigned task",
            )
        if task.status != WorkStatus.running or payload.status not in SERVICE_AGENT_TRANSITIONS:
            raise HTTPException(
                status_code=403,
                detail="service agent may only move its running task to review or blocked",
            )

    project = db.get(Project, task.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    if (
        project.status in {ProjectStatus.paused, ProjectStatus.archived, ProjectStatus.discontinued}
        and payload.status in {WorkStatus.ready, WorkStatus.running}
    ):
        raise HTTPException(
            status_code=409,
            detail="paused/archived/discontinued project cannot receive executable work",
        )

    if payload.status not in ALLOWED_TRANSITIONS[task.status]:
        raise HTTPException(
            status_code=409,
            detail=f"invalid transition {task.status.value} -> {payload.status.value}",
        )
    if payload.status == WorkStatus.running:
        project_wip = wip_count(db, task.project_id, None)
        agent_wip = (
            wip_count(db, task.project_id, task.assigned_agent_id)
            if task.assigned_agent_id is not None
            else project_wip
        )
        if project_wip >= 3 or agent_wip >= 3:
            raise HTTPException(status_code=409, detail="WIP limit reached")
        dependencies = list(
            db.scalars(
                select(Task)
                .join(TaskDependency, Task.id == TaskDependency.depends_on_task_id)
                .where(TaskDependency.task_id == task.id)
            )
        )
        if any(item.status != WorkStatus.done for item in dependencies):
            raise HTTPException(status_code=409, detail="task dependencies are not complete")
    if payload.status == WorkStatus.blocked and not payload.blocked_reason:
        raise HTTPException(status_code=422, detail="blocked_reason is required")
    if payload.status == WorkStatus.testing and not task.test_required:
        raise HTTPException(status_code=409, detail="task does not require a testing state")
    if payload.status == WorkStatus.done:
        reasons = task_done_reasons(db, task)
        if reasons:
            raise HTTPException(
                status_code=409,
                detail={"message": "DONE verification gate rejected", "reasons": reasons},
            )

    old_status = task.status
    task.status = payload.status
    task.blocked_reason = payload.blocked_reason if payload.status == WorkStatus.blocked else None
    record_audit(
        db,
        actor=actor,
        action="task.transitioned",
        entity_type="task",
        entity_id=str(task.id),
        payload={"from": old_status.value, "to": task.status.value},
    )
    db.commit()
    db.refresh(task)
    return task
