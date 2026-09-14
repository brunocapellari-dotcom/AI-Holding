from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext
from app.models.entities import Project, ProjectStatus, Task, WorkStatus
from app.models.routine import Routine
from app.services.audit import record_audit

MAX_DUE_ROUTINES = 100


def _next_future_due(
    scheduled_for: datetime,
    *,
    interval_minutes: int,
    now: datetime,
) -> tuple[datetime, int]:
    interval = timedelta(minutes=interval_minutes)
    next_due = scheduled_for + interval
    skipped_intervals = 0
    while next_due <= now:
        skipped_intervals += 1
        next_due += interval
    return next_due, skipped_intervals


def _task_identity(routine: Routine, scheduled_for: datetime) -> tuple[str, str]:
    slot = scheduled_for.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    task_key = f"RTN_{routine.id.hex[:12].upper()}_{slot}"
    idempotency_key = f"routine:{routine.id}:{slot}"
    return task_key, idempotency_key


def materialize_due_routines(
    db: Session,
    *,
    actor: ActorContext,
    execution_kinds: Sequence[str],
    project_id: UUID | None = None,
    now: datetime | None = None,
) -> list[UUID]:
    if not execution_kinds:
        return []

    effective_now = now or datetime.now(timezone.utc)
    supported_kinds = tuple(dict.fromkeys(execution_kinds))
    statement = (
        select(Routine)
        .join(Project, Project.id == Routine.project_id)
        .where(
            Routine.enabled.is_(True),
            Routine.next_due_at <= effective_now,
            Routine.execution_kind.in_(supported_kinds),
            Project.status == ProjectStatus.active,
        )
        .order_by(Routine.next_due_at.asc(), Routine.priority.asc(), Routine.created_at.asc())
        .limit(MAX_DUE_ROUTINES)
        .with_for_update(skip_locked=True)
    )
    if project_id is not None:
        statement = statement.where(Routine.project_id == project_id)

    created_task_ids: list[UUID] = []
    for routine in db.scalars(statement):
        scheduled_for = routine.next_due_at
        task_key, idempotency_key = _task_identity(routine, scheduled_for)
        existing = db.scalar(select(Task).where(Task.idempotency_key == idempotency_key))

        next_due, skipped_intervals = _next_future_due(
            scheduled_for,
            interval_minutes=routine.interval_minutes,
            now=effective_now,
        )
        routine.next_due_at = next_due

        if existing is None:
            task = Task(
                key=task_key,
                project_id=routine.project_id,
                title=routine.title,
                description=f"Scheduled routine execution for {routine.key}.",
                status=WorkStatus.planned,
                priority=routine.priority,
                assigned_agent_id=routine.assigned_agent_id,
                execution_kind=routine.execution_kind,
                auto_start=True,
                due_at=scheduled_for,
                idempotency_key=idempotency_key,
                metadata_json={
                    "routine_id": str(routine.id),
                    "routine_key": routine.key,
                    "scheduled_for": scheduled_for.isoformat(),
                    "skipped_intervals": skipped_intervals,
                },
            )
            db.add(task)
            db.flush()
            created_task_ids.append(task.id)
            action = "routine.materialized"
            task_id = task.id
        else:
            action = "routine.reconciled"
            task_id = existing.id

        record_audit(
            db,
            actor=actor,
            action=action,
            entity_type="routine",
            entity_id=str(routine.id),
            payload={
                "project_id": str(routine.project_id),
                "task_id": str(task_id),
                "execution_kind": routine.execution_kind,
                "scheduled_for": scheduled_for.isoformat(),
                "next_due_at": next_due.isoformat(),
                "skipped_intervals": skipped_intervals,
            },
        )

    if created_task_ids:
        db.flush()
    return created_task_ids
