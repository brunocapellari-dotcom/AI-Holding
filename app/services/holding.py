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
    RevenueEntry,
    RiskRegisterEntry,
)
from app.models.holding_evidence import CollectorExecution, SecurityFinding
from app.schemas.holding import (
    AlertOut,
    CostSummary,
    ExecutiveStateOut,
    HealthOut,
    HealthState,
    OperationalStatus,
    ProjectContractOut,
    ProjectRegistryEntryOut,
    RevenueSummary,
    SecurityLevel,
)
from app.schemas.holding_evidence import ExecutionFabricOut, ExecutionFabricProjectState


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _sync_collector_health_alerts(
    db: Session,
    *,
    project_id: UUID,
    collectors: list[CollectorRegistration],
    now: datetime,
) -> None:
    for collector in collectors:
        dedupe_key = f"collector-failing:{project_id}:{collector.key}"
        alert = db.scalar(select(HoldingAlert).where(HoldingAlert.dedupe_key == dedupe_key))

        if collector.status == "failing" and collector.consecutive_failures >= 3:
            details = {
                "collector_key": collector.key,
                "consecutive_failures": collector.consecutive_failures,
                "last_failure_at": (
                    collector.last_failure_at.isoformat()
                    if collector.last_failure_at is not None
                    else None
                ),
            }
            if alert is None:
                db.add(
                    HoldingAlert(
                        project_id=project_id,
                        level="action_required",
                        source="collector-health",
                        dedupe_key=dedupe_key,
                        title=f"Collector {collector.key} is failing",
                        details=details,
                        status="active",
                        occurrences=1,
                        last_seen_at=now,
                    )
                )
            else:
                previous_failures = alert.details.get("consecutive_failures")
                if previous_failures != collector.consecutive_failures:
                    alert.occurrences += 1
                alert.project_id = project_id
                alert.level = "action_required"
                alert.source = "collector-health"
                alert.title = f"Collector {collector.key} is failing"
                alert.details = details
                alert.status = "active"
                alert.last_seen_at = now
        elif collector.status == "healthy" and alert is not None and alert.status == "active":
            alert.status = "resolved"
            alert.last_seen_at = now
            alert.details = {
                "collector_key": collector.key,
                "consecutive_failures": 0,
                "recovered_at": now.isoformat(),
            }

    db.flush()


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


def summarize_revenues(db: Session, project_id: UUID | None = None) -> RevenueSummary:
    statement = select(RevenueEntry)
    if project_id is not None:
        statement = statement.where(RevenueEntry.project_id == project_id)
    entries = list(db.scalars(statement))

    totals_by_currency: dict[str, int] = {}
    by_source: dict[str, dict[str, int]] = {}
    for entry in entries:
        totals_by_currency[entry.currency] = (
            totals_by_currency.get(entry.currency, 0) + entry.amount_micros
        )
        source_totals = by_source.setdefault(entry.source, {})
        source_totals[entry.currency] = source_totals.get(entry.currency, 0) + entry.amount_micros

    return RevenueSummary(
        project_id=project_id,
        totals_by_currency=totals_by_currency,
        by_source=by_source,
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

    if persist:
        _sync_collector_health_alerts(
            db,
            project_id=project_id,
            collectors=collectors,
            now=now,
        )

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
                HoldingAlert.project_id == project_id,
                HoldingAlert.status == "active",
            )
        )
    )
    security_findings = list(
        db.scalars(
            select(SecurityFinding).where(
                SecurityFinding.project_id == project_id,
                SecurityFinding.status.in_(["open", "mitigating"]),
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
    security_penalty = min(
        45,
        sum(
            35
            if finding.severity == "critical"
            else 20
            if finding.severity == "high"
            else 8
            if finding.severity == "medium"
            else 2
            for finding in security_findings
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
        - security_penalty
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
    if security_findings:
        reasons.append({"kind": "security_findings", "count": len(security_findings)})
    if blocked_dependencies:
        reasons.append({"kind": "blocking_dependencies", "count": len(blocked_dependencies)})

    critical_signal = (
        any(risk.severity == "critical" for risk in open_risks)
        or any(alert.level == "critical" for alert in active_alerts)
        or any(finding.severity == "critical" for finding in security_findings)
    )
    degraded_signal = (
        bool(failing_collectors)
        or any(alert.level == "action_required" for alert in active_alerts)
        or any(finding.severity == "high" for finding in security_findings)
    )

    state: HealthState
    if operational_status == "cancelled":
        state = "offline"
    elif operational_status == "blocked" or blocked_dependencies:
        state = "blocked"
    elif critical_signal or score < 50:
        state = "at_risk"
    elif degraded_signal or score < 80 or operational_status == "paused":
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
        "security": {
            "open_findings": len(security_findings),
            "high": sum(finding.severity == "high" for finding in security_findings),
            "critical": sum(
                finding.severity == "critical" for finding in security_findings
            ),
        },
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
    security_findings = list(
        db.scalars(
            select(SecurityFinding).where(
                SecurityFinding.project_id == project_id,
                SecurityFinding.status.in_(["open", "mitigating"]),
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
        revenue=summarize_revenues(db, project_id),
        security={
            "level": security_level,
            "open_risks": len(risks),
            "critical_risks": sum(risk.severity == "critical" for risk in risks),
            "open_findings": len(security_findings),
            "high_findings": sum(
                finding.severity == "high" for finding in security_findings
            ),
            "critical_findings": sum(
                finding.severity == "critical" for finding in security_findings
            ),
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


def project_registry(db: Session) -> list[ProjectRegistryEntryOut]:
    projects = list(db.scalars(select(Project).order_by(Project.priority, Project.name)))
    profiles = {
        profile.project_id: profile for profile in db.scalars(select(ProjectOperationalProfile))
    }
    rows: list[ProjectRegistryEntryOut] = []
    for project in projects:
        profile = profiles.get(project.id)
        operational_status = cast(
            OperationalStatus,
            profile.operational_status if profile else "planned",
        )
        security_level = cast(
            SecurityLevel,
            profile.security_level if profile else "internal",
        )
        rows.append(
            ProjectRegistryEntryOut(
                project_id=project.id,
                project_key=project.key,
                name=project.name,
                repository=project.repository,
                legacy_status=project.status.value,
                operational_status=operational_status,
                priority=project.priority,
                autonomy_level=project.autonomy_level,
                business_unit=project.business_unit,
                mission=profile.mission if profile else project.strategic_goal,
                current_phase=profile.current_phase if profile else None,
                knowledge_namespace=profile.knowledge_namespace if profile else None,
                security_level=security_level,
                budget_micros=profile.budget_micros if profile else 0,
                budget_currency=profile.budget_currency if profile else "BRL",
                health=compute_project_health(db, project.id, persist=False),
            )
        )
    return rows


def executive_state(db: Session) -> ExecutiveStateOut:
    now = datetime.now(UTC)
    registry = project_registry(db)

    buckets: dict[str, list[dict[str, object]]] = {
        "running": [],
        "completed": [],
        "failed": [],
        "blocked": [],
    }
    priorities: list[dict[str, object]] = []
    for project in registry:
        item: dict[str, object] = {
            "project_id": str(project.project_id),
            "key": project.project_key,
            "name": project.name,
            "priority": project.priority,
            "status": project.operational_status,
            "health": project.health.state,
            "health_score": project.health.score,
        }
        if project.operational_status in buckets:
            buckets[project.operational_status].append(item)
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
        revenues={"summary": summarize_revenues(db).model_dump()},
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



def execution_fabric_state(db: Session) -> ExecutionFabricOut:
    now = datetime.now(UTC)
    registry = project_registry(db)
    projects_by_id = {row.project_id: row for row in registry}

    collectors = list(
        db.scalars(
            select(CollectorRegistration).where(
                CollectorRegistration.key == "gcp-cloud-build"
            )
        )
    )
    latest_by_project: dict[UUID, CollectorExecution] = {}
    for collector in collectors:
        execution = db.scalar(
            select(CollectorExecution)
            .where(CollectorExecution.collector_id == collector.id)
            .order_by(CollectorExecution.started_at.desc(), CollectorExecution.id.desc())
            .limit(1)
        )
        if execution is not None:
            latest_by_project[collector.project_id] = execution

    projects: list[ExecutionFabricProjectState] = []
    totals = {
        "success": 0,
        "working": 0,
        "queued": 0,
        "failure": 0,
        "unknown": 0,
    }

    for project_id, row in projects_by_id.items():
        if not row.repository:
            continue

        execution = latest_by_project.get(project_id)
        cloud_state = "unknown"
        build_id: str | None = None
        branch: str | None = None
        commit_sha: str | None = None
        log_url: str | None = None
        evidence_uri: str | None = None
        observed_at: datetime | None = None

        if execution is not None:
            observed_at = execution.finished_at or execution.started_at
            evidence = execution.evidence if isinstance(execution.evidence, list) else []
            snapshot = evidence[0] if evidence and isinstance(evidence[0], dict) else {}
            raw_status = str(snapshot.get("status") or "").upper()
            if raw_status == "SUCCESS":
                cloud_state = "success"
            elif raw_status in {"WORKING"}:
                cloud_state = "working"
            elif raw_status in {"QUEUED", "PENDING"}:
                cloud_state = "queued"
            elif raw_status in {
                "FAILURE",
                "INTERNAL_ERROR",
                "TIMEOUT",
                "CANCELLED",
                "EXPIRED",
            }:
                cloud_state = "failure"
            elif execution.status == "failure":
                cloud_state = "failure"

            raw_id = snapshot.get("id")
            if raw_id is not None:
                build_id = str(raw_id)

            substitutions = snapshot.get("substitutions")
            if isinstance(substitutions, dict):
                raw_branch = substitutions.get("BRANCH_NAME")
                raw_commit = substitutions.get("COMMIT_SHA")
                if isinstance(raw_branch, str):
                    branch = raw_branch
                if isinstance(raw_commit, str):
                    commit_sha = raw_commit

            raw_log_url = snapshot.get("log_url")
            if isinstance(raw_log_url, str):
                log_url = raw_log_url

            metadata = (
                execution.metadata_json
                if isinstance(execution.metadata_json, dict)
                else {}
            )
            raw_evidence_uri = metadata.get("evidence_uri")
            if isinstance(raw_evidence_uri, str):
                evidence_uri = raw_evidence_uri

        totals[cloud_state] = totals.get(cloud_state, 0) + 1
        projects.append(
            ExecutionFabricProjectState(
                project_id=project_id,
                project_key=row.project_key,
                name=row.name,
                repository=row.repository,
                health_state=row.health.state,
                health_score=row.health.score,
                cloud_build_state=cloud_state,
                build_id=build_id,
                branch=branch,
                commit_sha=commit_sha,
                log_url=log_url,
                evidence_uri=evidence_uri,
                observed_at=observed_at,
            )
        )

    projects.sort(key=lambda item: (item.cloud_build_state, item.name.casefold()))
    return ExecutionFabricOut(
        generated_at=now,
        totals=totals,
        projects=projects,
    )
