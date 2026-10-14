from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from typing import NoReturn

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext
from app.db.session import SessionLocal
from app.models.agent_identity import AgentIdentity
from app.models.entities import (
    Agent,
    AgentStatus,
    Incident,
    IncidentStatus,
    Project,
    Run,
    RunStatus,
    Task,
    WorkStatus,
)
from app.services.audit import record_audit

PMO_AGENT_KEY = "PMO_IA"
HOLDING_PROJECT_KEY = "AI_HOLDING"
EXECUTION_KIND = "control_plane_health"
ACCEPTANCE_IDEMPOTENCY_PREFIX = "prod-pmo-acceptance-"
ACCEPTANCE_ACTOR = ActorContext(
    name="production-acceptance-job",
    actor_type="system",
    authenticated=True,
)


@dataclass(frozen=True)
class AcceptanceContext:
    release_id: str
    release_key: str
    idempotency_key: str
    task_key: str


def acceptance_context(release_id: str) -> AcceptanceContext:
    normalized = release_id.strip()
    if not normalized:
        raise RuntimeError("RELEASE_ID is required")
    release_key = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return AcceptanceContext(
        release_id=normalized,
        release_key=release_key,
        idempotency_key=f"{ACCEPTANCE_IDEMPOTENCY_PREFIX}{release_key}",
        task_key=f"PMO_PROD_HEALTH_{release_key.upper()}",
    )


def _canonical_entities(db: Session) -> tuple[Agent, Project]:
    agent = db.scalar(select(Agent).where(Agent.key == PMO_AGENT_KEY))
    if agent is None:
        raise RuntimeError("canonical PMO_IA agent is missing")
    project = db.scalar(select(Project).where(Project.key == HOLDING_PROJECT_KEY))
    if project is None:
        raise RuntimeError("canonical AI_HOLDING project is missing")
    identity = db.scalar(select(AgentIdentity).where(AgentIdentity.agent_id == agent.id))
    if identity is None:
        raise RuntimeError("PMO_IA has no canonical runtime identity binding")
    return agent, project


def _supersede_stale_acceptance_tasks(
    db: Session,
    *,
    agent: Agent,
    project: Project,
    context: AcceptanceContext,
) -> int:
    stale_tasks = list(
        db.scalars(
            select(Task).where(
                Task.project_id == project.id,
                Task.assigned_agent_id == agent.id,
                Task.execution_kind == EXECUTION_KIND,
                Task.idempotency_key.like(f"{ACCEPTANCE_IDEMPOTENCY_PREFIX}%"),
                Task.idempotency_key != context.idempotency_key,
                Task.status.in_(
                    (
                        WorkStatus.planned,
                        WorkStatus.ready,
                        WorkStatus.running,
                        WorkStatus.review,
                    )
                ),
            )
        )
    )
    for task in stale_tasks:
        if task.status == WorkStatus.running:
            raise RuntimeError(
                f"prior production acceptance is still running: {task.idempotency_key}"
            )

    superseded = 0
    for task in stale_tasks:
        previous_status = task.status
        task.status = WorkStatus.cancelled
        task.blocked_reason = f"superseded by production acceptance {context.release_key}"
        record_audit(
            db,
            actor=ACCEPTANCE_ACTOR,
            action="pmo.production_acceptance.superseded",
            entity_type="task",
            entity_id=str(task.id),
            payload={
                "previous_status": previous_status.value,
                "replacement_release_key": context.release_key,
            },
        )
        superseded += 1
    return superseded


def prepare_acceptance(db: Session, release_id: str) -> dict[str, object]:
    context = acceptance_context(release_id)
    agent, project = _canonical_entities(db)
    superseded_tasks = _supersede_stale_acceptance_tasks(
        db,
        agent=agent,
        project=project,
        context=context,
    )

    if agent.status == AgentStatus.degraded:
        raise RuntimeError("PMO_IA is degraded and cannot enter production acceptance")
    if agent.status == AgentStatus.disabled:
        agent.status = AgentStatus.active

    task = db.scalar(select(Task).where(Task.idempotency_key == context.idempotency_key))
    if task is None:
        task = Task(
            key=context.task_key,
            project_id=project.id,
            title=f"Production PMO health acceptance {context.release_key}",
            description=(
                "Bounded production acceptance for the PMO worker and authenticated Control Plane."
            ),
            status=WorkStatus.ready,
            priority=0,
            assigned_agent_id=agent.id,
            execution_kind=EXECUTION_KIND,
            idempotency_key=context.idempotency_key,
            metadata_json={
                "purpose": "production_acceptance",
                "release_key": context.release_key,
            },
        )
        db.add(task)
        db.flush()
    else:
        if (
            task.project_id != project.id
            or task.assigned_agent_id != agent.id
            or task.execution_kind != EXECUTION_KIND
        ):
            raise RuntimeError("production acceptance task identity drift detected")
        if task.status in {WorkStatus.blocked, WorkStatus.cancelled}:
            raise RuntimeError(
                f"production acceptance task is terminally unsafe: {task.status.value}"
            )

    record_audit(
        db,
        actor=ACCEPTANCE_ACTOR,
        action="pmo.production_acceptance.prepared",
        entity_type="task",
        entity_id=str(task.id),
        payload={
            "agent_id": str(agent.id),
            "project_id": str(project.id),
            "release_key": context.release_key,
            "task_status": task.status.value,
            "superseded_tasks": superseded_tasks,
        },
    )
    db.commit()
    return {
        "release_key": context.release_key,
        "task_id": str(task.id),
        "task_status": task.status.value,
        "agent_id": str(agent.id),
        "agent_status": agent.status.value,
        "superseded_tasks": superseded_tasks,
    }


def _acceptance_run(db: Session, task: Task) -> Run | None:
    return db.scalar(
        select(Run)
        .where(Run.task_id == task.id)
        .order_by(Run.attempt.desc(), Run.created_at.desc())
        .limit(1)
    )


def _evidence_errors(run: Run) -> list[str]:
    errors: list[str] = []
    output = run.output_metadata
    if output.get("execution_kind") != EXECUTION_KIND:
        errors.append("run output execution_kind is invalid")
    evidence = output.get("evidence")
    if not isinstance(evidence, dict):
        return [*errors, "run output has no structured health evidence"]
    for path in ("/health", "/ready"):
        item = evidence.get(path)
        if not isinstance(item, dict) or item.get("status_code") != 200:
            errors.append(f"{path} did not return accepted evidence")
    return errors


def _open_worker_incidents(db: Session, task: Task) -> list[Incident]:
    candidates = db.scalars(
        select(Incident).where(
            Incident.project_id == task.project_id,
            Incident.source == "pmo-worker",
            Incident.status != IncidentStatus.resolved,
        )
    )
    return [item for item in candidates if item.details.get("task_id") == str(task.id)]


def _fail_acceptance(
    db: Session,
    *,
    agent: Agent,
    context: AcceptanceContext,
    errors: list[str],
) -> NoReturn:
    if agent.status != AgentStatus.disabled:
        agent.status = AgentStatus.disabled
    record_audit(
        db,
        actor=ACCEPTANCE_ACTOR,
        action="pmo.production_acceptance.failed",
        entity_type="agent",
        entity_id=str(agent.id),
        payload={"release_key": context.release_key, "errors": errors},
    )
    db.commit()
    raise RuntimeError("; ".join(errors))


def finalize_acceptance(db: Session, release_id: str) -> dict[str, object]:
    context = acceptance_context(release_id)
    agent, _ = _canonical_entities(db)
    task = db.scalar(select(Task).where(Task.idempotency_key == context.idempotency_key))

    errors: list[str] = []
    run: Run | None = None
    if task is None:
        errors.append("production acceptance task is missing")
    else:
        if task.status not in {WorkStatus.review, WorkStatus.done}:
            errors.append(f"task did not reach review: {task.status.value}")
        run = _acceptance_run(db, task)
        if run is None:
            errors.append("production acceptance run is missing")
        else:
            if run.agent_id != agent.id:
                errors.append("production acceptance run used the wrong agent")
            if run.status != RunStatus.succeeded:
                errors.append(f"production acceptance run did not succeed: {run.status.value}")
            else:
                errors.extend(_evidence_errors(run))
        if _open_worker_incidents(db, task):
            errors.append("production acceptance produced an unresolved PMO worker incident")

    if errors:
        _fail_acceptance(db, agent=agent, context=context, errors=errors)

    if task is None or run is None:
        _fail_acceptance(
            db,
            agent=agent,
            context=context,
            errors=["production acceptance reached an inconsistent internal state"],
        )

    if task.status == WorkStatus.review:
        task.status = WorkStatus.done
        task.blocked_reason = None

    record_audit(
        db,
        actor=ACCEPTANCE_ACTOR,
        action="pmo.production_acceptance.verified",
        entity_type="task",
        entity_id=str(task.id),
        payload={
            "agent_id": str(agent.id),
            "run_id": str(run.id),
            "release_key": context.release_key,
            "evidence": run.output_metadata.get("evidence", {}),
        },
    )
    db.commit()
    return {
        "release_key": context.release_key,
        "task_id": str(task.id),
        "task_status": task.status.value,
        "run_id": str(run.id),
        "run_status": run.status.value,
        "agent_status": agent.status.value,
    }


def acceptance_status(db: Session, release_id: str) -> dict[str, object]:
    context = acceptance_context(release_id)
    agent, _ = _canonical_entities(db)
    task = db.scalar(select(Task).where(Task.idempotency_key == context.idempotency_key))
    run = _acceptance_run(db, task) if task is not None else None
    return {
        "release_key": context.release_key,
        "agent_status": agent.status.value,
        "task_id": str(task.id) if task else None,
        "task_status": task.status.value if task else None,
        "run_id": str(run.id) if run else None,
        "run_status": run.status.value if run else None,
    }


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "finalize", "status"}:
        raise RuntimeError("usage: python -m app.pmo_acceptance <prepare|finalize|status>")
    release_id = os.getenv("RELEASE_ID", "")
    with SessionLocal() as db:
        if sys.argv[1] == "prepare":
            result = prepare_acceptance(db, release_id)
        elif sys.argv[1] == "finalize":
            result = finalize_acceptance(db, release_id)
        else:
            result = acceptance_status(db, release_id)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
