from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Decision, DecisionStatus, Project, Run, RunStatus, Task, WorkStatus
from app.models.holding import (
    CollectorRegistration,
    CostEntry,
    DependencyEdge,
    HoldingAlert,
    IntegrationState,
    ProjectHealthSnapshot,
    ProjectOperationalProfile,
    RiskRegisterEntry,
)
from app.schemas.holding import (
    AlertOut,
    CostSummary,
    ExecutiveStateOut,
    HealthOut,
    HealthState,
    OperationalStatus,
    ProjectContractOut,
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def summarize_costs(db: Session, project_id: UUID | None = None) -> CostSummary:
    statement = select(CostEntry)
    if project_id is not None:
        statement = statement.where(CostEntry.project_id == project_id)
    entries = list(db.scalars(statement))

    totals_by_currency: dict[str, int] = {}
    by_category: dict[str, dict[str, int]] = {}
    by_provider: dict[str, dict[str, int]] = {}
    for entry in entries:
        totals_by_currency[entry.currency] = (
            totals_by_currency.get(entry.currency, 0) + entry.amount_micros
        )
        category_totals = by_category.setdefault(entry.category, {})
        category_totals[entry.currency] = (
            category_totals.get(entry.currency, 0) + entry.amount_micros
        )
        provider_totals = by_provider.setdefault(entry.provider, {})
        provider_totals[entry.currency] = (
            provider_totals.get(entry.currency, 0) + entry.amount_micros
        )

    return CostSummary(
        project_id=project_id,
        totals_by_currency=totals_by_currency,
        by_category=by_category,
        by_provider=by_provider,
    )


def compute_project_health(db: Session, project_id: UUID, persist: bool = True) -> HealthOut:
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    profile = db.get(ProjectOperationalProfile, project_id)
    operational_status = (
        cast(OperationalStatus, profile.operational_status) if profile else "planned"
    )
    now = datetime.now(UTC)
    reasons: list[object] = []

    collectors = list(
        db.scalars(
            select(CollectorRegistration).where(CollectorRegistration.project_id == project_id)
        )
    )
    stale_collectors = 0
    failing_collectors = 0
    for collector in collectors:
        if collector.status == "disabled":
            continue
        if collector.status in {"degraded", "failing"}:
            failing_collectors += 1
        if collector.last_success_at is None:
            stale_collectors += 1
            continue
        age = (now - _utc(collector.last_success_at)).total_seconds()
        if age > collector.freshness_sla_seconds:
            stale_collectors += 1

    blocked_tasks = list(
        db.scalars(
            select(Task).where(Task.project_id == project_id, Task.status == WorkStatus.blocked)
        )
    )
    failed_runs = int(
        db.scalar(
            select(func.count(Run.id))
            .join(Task, Run.task_id == Task.id)
            .where(Task.project_id == project_id, Run.status == RunStatus.failed)
        )
        or 0
    )
    open_risks = list(
        db.scalars(
            select(RiskRegisterEntry).where(
                RiskRegisterEntry.project_id == project_id,
                RiskRegisterEntry.status.in_(["open", "mitigating"]),
            )
        )
    )
    active_alerts = list(
        db.scalars(
            select(HoldingAlert).where(
                HoldingAlert.project_id == project_id, HoldingAlert.status == "active"
            )
        )
    )
    blocked_dependencies = list(
        db.scalars(
            select(DependencyEdge).where(
                DependencyEdge.source_type == "project",
                DependencyEdge.source_key == project.key,
                DependencyEdge.blocking.is_(True),
                DependencyEdge.status.in_(["blocked", "offline"]),
            )
        )
    )

    collector_penalty = min(40, stale_collectors * 12 + failing_collectors * 8)
    task_penalty = min(40, len(blocked_tasks) * 20)
    run_penalty = min(20, failed_runs * 5)
    risk_penalty = min(
        40,
        sum(
            30 if risk.severity == "critical" else 15 if risk.severity == "high" else 5
            for risk in open_risks
        ),
    )
    alert_penalty = min(
        35,
        sum(
            25
            if alert.level == "critical"
            else 12
            if alert.level == "action_required"
            else 4
            for alert in active_alerts
        ),
    )
    dependency_penalty = 35 if blocked_dependencies else 0
    score = max(
        0,
        100
        - collector_penalty
        - task_penalty
        - run_penalty
        - risk_penalty
        - alert_penalty
        - dependency_penalty,
    )

    if stale_collectors:
        reasons.append({"kind": "collector_stale", "count": stale_collectors})
    if failing_collectors:
        reasons.append({"kind": "collector_degraded", "count": failing_collectors})
    if blocked_tasks:
        reasons.append({"kind": "blocked_tasks", "count": len(blocked_tasks)})
    if failed_runs:
        reasons.append({"kind": "failed_runs", "count": failed_runs})
    if open_risks:
        reasons.append({"kind": "open_risks", "count": len(open_risks)})
    if active_alerts:
        reasons.append({"kind": "active_alerts", "count": len(active_alerts)})
    if blocked_dependencies:
        reasons.append({"kind": "blocking_dependencies", "count": len(blocked_dependencies)})

    state: HealthState
    if operational_status == "cancelled":
        state = "offline"
    elif operational_status == "blocked" or blocked_dependencies:
        state = "blocked"
    elif score < 50:
        state = "at_risk"
    elif score < 80 or operational_status == "paused":
        state = "degraded"
    else:
        state = "healthy"

    dimensions: dict[str, object] = {
        "operational_status": operational_status,
        "collectors": {
            "total": len(collectors),
            "stale": stale_collectors,
            "degraded_or_failing": failing_collectors,
        },
        "tasks": {"blocked": len(blocked_tasks)},
        "runs": {"failed_total": failed_runs},
        "risks": {"open": len(open_risks)},
        "alerts": {"active": len(active_alerts)},
        "dependencies": {"blocking_unhealthy": len(blocked_dependencies)},
    }

    if persist:
        db.add(
            ProjectHealthSnapshot(
                project_id=project_id,
                state=state,
                score=score,
                dimensions=dimensions,
                reasons=reasons,
                computed_at=now,
            )
        )
        db.flush()

    return HealthOut(
        project_id=project_id,
        state=state,
        score=score,
        dimensions=dimensions,
        reasons=reasons,
        computed_at=now,
    )


def project_contract(db: Session, project_id: UUID) -> ProjectContractOut:
    project = db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    profile = db.get(ProjectOperationalProfile, project_id)
    operational_status = (
        cast(OperationalStatus, profile.operational_status) if profile else "planned"
    )
    security_level = profile.security_level if profile else "internal"
    health = compute_project_health(db, project_id, persist=False)
    tasks = list(
        db.scalars(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.priority, Task.created_at)
        )
    )
    blockers = [task for task in tasks if task.status == WorkStatus.blocked]
    collectors = list(
        db.scalars(
            select(CollectorRegistration).where(CollectorRegistration.project_id == project_id)
        )
    )
    risks = list(
        db.scalars(
            select(RiskRegisterEntry).where(
                RiskRegisterEntry.project_id == project_id,
                RiskRegisterEntry.status.in_(["open", "mitigating"]),
            )
        )
    )
    alerts = list(
        db.scalars(
            select(HoldingAlert)
            .where(HoldingAlert.project_id == project_id, HoldingAlert.status == "active")
            .order_by(HoldingAlert.level, HoldingAlert.last_seen_at.desc())
        )
    )
    capabilities = project.metadata_json.get("capabilities", [])
    if not isinstance(capabilities, list):
        capabilities = []

    return ProjectContractOut(
        project_id=project.id,
        project_key=project.key,
        name=project.name,
        status=operational_status,
        capabilities=capabilities,
        tasks=[
            {
                "id": str(task.id),
                "key": task.key,
                "status": task.status.value,
                "priority": task.priority,
                "due_at": task.due_at.isoformat() if task.due_at else None,
            }
            for task in tasks
        ],
        blockers=[
            {
                "id": str(task.id),
                "key": task.key,
                "reason": task.blocked_reason,
            }
            for task in blockers
        ],
        cost=summarize_costs(db, project_id),
        security={
            "level": security_level,
            "open_risks": len(risks),
            "critical_risks": sum(risk.severity == "critical" for risk in risks),
        },
        data_health={
            "collector_count": len(collectors),
            "healthy_collectors": sum(collector.status == "healthy" for collector in collectors),
            "unhealthy_collectors": sum(
                collector.status in {"degraded", "failing"} for collector in collectors
            ),
        },
        health=health,
        alerts=[AlertOut.model_validate(alert) for alert in alerts],
    )


def executive_state(db: Session) -> ExecutiveStateOut:
    now = datetime.now(UTC)
    projects = list(db.scalars(select(Project).order_by(Project.priority, Project.name)))
    profiles = {
        profile.project_id: profile for profile in db.scalars(select(ProjectOperationalProfile))
    }

    buckets: dict[str, list[dict[str, object]]] = {
        "running": [],
        "completed": [],
        "failed": [],
        "blocked": [],
    }
    priorities: list[dict[str, object]] = []
    for project in projects:
        profile = profiles.get(project.id)
        status = profile.operational_status if profile else "planned"
        item: dict[str, object] = {
            "project_id": str(project.id),
            "key": project.key,
            "name": project.name,
            "priority": project.priority,
            "status": status,
        }
        if status in buckets:
            buckets[status].append(item)
        priorities.append(item)

    owner_decisions = list(
        db.scalars(
            select(Decision).where(
                Decision.requires_human.is_(True), Decision.status == DecisionStatus.pending
            )
        )
    )
    risks = list(
        db.scalars(
            select(RiskRegisterEntry)
            .where(RiskRegisterEntry.status.in_(["open", "mitigating"]))
            .order_by(RiskRegisterEntry.severity.desc(), RiskRegisterEntry.impact.desc())
        )
    )
    integrations = list(db.scalars(select(IntegrationState)))

    return ExecutiveStateOut(
        generated_at=now,
        running=buckets["running"],
        completed=buckets["completed"],
        failed=buckets["failed"],
        blocked=buckets["blocked"],
        owner_actions=[
            {
                "decision_id": str(decision.id),
                "project_id": str(decision.project_id),
                "title": decision.title,
                "risk_level": decision.risk_level.value,
            }
            for decision in owner_decisions
        ],
        costs={
            "summary": summarize_costs(db).model_dump(),
            "integrations": {state.service_key: state.status for state in integrations},
        },
        risks=[
            {
                "risk_id": str(risk.id),
                "project_id": str(risk.project_id) if risk.project_id else None,
                "key": risk.key,
                "severity": risk.severity,
                "status": risk.status,
            }
            for risk in risks
        ],
        priorities=priorities,
    )
