from __future__ import annotations

from collections.abc import Sequence
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
from app.schemas.policy import PolicyEvaluationRequest, PolicyOutcome
from app.services.audit import record_audit
from app.services.execution_policy import execution_policy_profile
from app.services.policy import PolicyDecision, evaluate_policy
from app.services.routines import materialize_due_routines

ACTIVE_RUN_STATUSES = (RunStatus.queued, RunStatus.running)
MAX_POLICY_CANDIDATES = 25
MAX_AUTO_READY_CANDIDATES = 100


def _policy_decision(project: Project, agent: Agent, task: Task) -> PolicyDecision | None:
    profile = execution_policy_profile(task.execution_kind)
    if profile is None:
        return None

    request = PolicyEvaluationRequest(
        action_key=f"TASK_{task.id.hex.upper()}",
        project_id=project.id,
        agent_id=agent.id,
        action_type=profile.action_type,
        summary=f"Execute task {task.key}",
        risk_level=profile.risk_level,
        irreversible=profile.irreversible,
        external_party_effect=profile.external_party_effect,
        sensitive_data=profile.sensitive_data,
    )
    return evaluate_policy(project, agent, request)


def promote_auto_ready_tasks(
    db: Session,
    *,
    actor: ActorContext,
    execution_kinds: Sequence[str],
    project_id: UUID | None = None,
) -> list[UUID]:
    if not execution_kinds:
        return []

    supported_kinds = tuple(dict.fromkeys(execution_kinds))
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

    statement = (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .where(
            Task.status == WorkStatus.planned,
            Task.auto_start.is_(True),
            Task.execution_kind.in_(supported_kinds),
            Project.status == ProjectStatus.active,
            ~incomplete_dependency,
        )
        .order_by(
            Task.priority.asc(),
            Task.due_at.asc().nulls_last(),
            Task.created_at.asc(),
        )
        .limit(MAX_AUTO_READY_CANDIDATES)
        .with_for_update(skip_locked=True)
    )
    if project_id is not None:
        statement = statement.where(Task.project_id == project_id)

    promoted: list[UUID] = []
    for task in db.scalars(statement):
        task.status = WorkStatus.ready
        task.blocked_reason = None
        promoted.append(task.id)
        record_audit(
            db,
            actor=actor,
            action="task.auto_ready",
            entity_type="task",
            entity_id=str(task.id),
            payload={
                "project_id": str(task.project_id),
                "execution_kind": task.execution_kind,
            },
        )

    if promoted:
        db.flush()
    return promoted


def claim_next_task(
    db: Session,
    *,
    agent: Agent,
    actor: ActorContext,
    execution_kinds: Sequence[str],
    project_id: UUID | None = None,
) -> tuple[Task, Run] | None:
    if agent.status != AgentStatus.active or not execution_kinds:
        return None

    supported_kinds = tuple(dict.fromkeys(execution_kinds))
    materialize_due_routines(
        db,
        actor=actor,
        execution_kinds=supported_kinds,
        project_id=project_id,
    )
    promote_auto_ready_tasks(
        db,
        actor=actor,
        execution_kinds=supported_kinds,
        project_id=project_id,
    )

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
            Task.execution_kind.in_(supported_kinds),
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
        .limit(MAX_POLICY_CANDIDATES)
        .with_for_update(skip_locked=True)
    )
    if project_id is not None:
        statement = statement.where(Task.project_id == project_id)

    candidates = list(db.scalars(statement))
    task: Task | None = None
    policy: PolicyDecision | None = None
    for candidate in candidates:
        project = db.get(Project, candidate.project_id)
        if project is None:
            continue
        candidate_policy = _policy_decision(project, agent, candidate)
        if candidate_policy is None or candidate_policy.outcome != PolicyOutcome.allow:
            continue
        task = candidate
        policy = candidate_policy
        break

    if task is None or policy is None:
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
        input_metadata={
            "claim_source": "pmo",
            "execution_kind": task.execution_kind,
            "policy": {
                "outcome": policy.outcome.value,
                "required_autonomy": policy.required_autonomy,
                "effective_autonomy": policy.effective_autonomy,
            },
        },
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
            "execution_kind": task.execution_kind,
            "policy_outcome": policy.outcome.value,
            "policy_required_autonomy": policy.required_autonomy,
            "policy_effective_autonomy": policy.effective_autonomy,
        },
    )
    return task, run
