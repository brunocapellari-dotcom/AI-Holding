from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.db.session import get_db
from app.models.entities import Milestone, Project, Task, TaskDependency, WorkStatus
from app.schemas.api import TaskCreate, TaskOut, TaskTransition
from app.services.audit import record_audit

router = APIRouter(prefix="/tasks", tags=["tasks"])

ALLOWED_TRANSITIONS: dict[WorkStatus, set[WorkStatus]] = {
    WorkStatus.planned: {WorkStatus.ready, WorkStatus.cancelled},
    WorkStatus.ready: {WorkStatus.running, WorkStatus.blocked, WorkStatus.cancelled},
    WorkStatus.running: {WorkStatus.review, WorkStatus.blocked, WorkStatus.cancelled},
    WorkStatus.blocked: {WorkStatus.ready, WorkStatus.cancelled},
    WorkStatus.review: {WorkStatus.running, WorkStatus.done, WorkStatus.blocked},
    WorkStatus.done: set(),
    WorkStatus.cancelled: set(),
}


@router.get("", response_model=list[TaskOut])
def list_tasks(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)) -> list[Task]:
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    return list(
        db.scalars(select(Task).order_by(Task.priority, Task.created_at).limit(limit).offset(offset))
    )


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> Task:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if payload.milestone_id:
        milestone = db.get(Milestone, payload.milestone_id)
        if not milestone or milestone.project_id != project.id:
            raise HTTPException(status_code=400, detail="milestone does not belong to project")

    existing = db.scalar(select(Task).where(Task.idempotency_key == payload.idempotency_key))
    if existing:
        return existing

    dependency_ids = list(dict.fromkeys(payload.depends_on))
    for dependency_id in dependency_ids:
        dependency = db.get(Task, dependency_id)
        if not dependency or dependency.project_id != project.id:
            raise HTTPException(status_code=400, detail="invalid cross-project or missing dependency")

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
        raise HTTPException(status_code=409, detail="task key or idempotency key already exists") from exc

    record_audit(
        db,
        actor=actor,
        action="task.created",
        entity_type="task",
        entity_id=str(task.id),
        payload={"project_id": str(task.project_id), "dependencies": len(dependency_ids)},
    )
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/transition", response_model=TaskOut)
def transition_task(
    task_id: UUID,
    payload: TaskTransition,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(get_actor),
) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if payload.status not in ALLOWED_TRANSITIONS[task.status]:
        raise HTTPException(
            status_code=409,
            detail=f"invalid transition {task.status.value} -> {payload.status.value}",
        )
    if payload.status == WorkStatus.running:
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
