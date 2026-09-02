from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.actor import ActorContext
from app.models.entities import (
    Agent,
    AgentStatus,
    Project,
    ProjectStatus,
    Run,
    RunStatus,
    Task,
    TaskDependency,
    WorkStatus,
)
from app.services.audit import record_audit

ACTIVE_RUN_STATUSES = (RunStatus.queued, RunStatus.running)


def claim_next_task(
    db: Session,
    *,
    agent: Agent,
    actor: ActorContext,
    project_id: UUID | None = None,
) -> tuple[Task, Run] | None:
    if agent.status != AgentStatus.active:
        return None

    dependency = aliased(Task)
    incomplete_dependency = exists(
        select(1)
        .select_from(TaskDependency)
        .join(dependency, dependency.id == TaskDependency.depends_on_task_id)
        .where(
            TaskDependency.task_id == Task.id,
            dependency.status != WorkStatus.done,
        )
    )
    active_run = exists(
        select(1)
        .select_from(Run)
        .where(
            Run.task_id == Task.id,
            Run.status.in_(ACTIVE_RUN_STATUSES),
        )
    )

    statement = (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .where(
            Task.status == WorkStatus.ready,
            Project.status == ProjectStatus.active,
            or_(Task.assigned_agent_id.is_(None), Task.assigned_agent_id == agent.id),
            ~incomplete_dependency,
            ~active_run,
        )
        .order_by(
            Task.priority.asc(),
            Task.due_at.asc().nulls_last(),
            Task.created_at.asc(),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if project_id is not None:
        statement = statement.where(Task.project_id == project_id)

    task = db.scalar(statement)
    if task is None:
        return None

    last_attempt = db.scalar(select(func.max(Run.attempt)).where(Run.task_id == task.id)) or 0
    task.status = WorkStatus.running
    task.assigned_agent_id = agent.id
    task.blocked_reason = None

    run = Run(
        task_id=task.id,
        agent_id=agent.id,
        status=RunStatus.queued,
        attempt=last_attempt + 1,
        input_metadata={"claim_source": "pmo"},
    )
    db.add(run)
    db.flush()

    record_audit(
        db,
        actor=actor,
        action="task.claimed",
        entity_type="task",
        entity_id=str(task.id),
        payload={
            "agent_id": str(agent.id),
            "project_id": str(task.project_id),
            "run_id": str(run.id),
            "attempt": run.attempt,
        },
    )
    return task, run
