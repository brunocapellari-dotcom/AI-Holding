from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.control_plane import (
    BlockerRecord,
    DeploymentRecord,
    EvidenceRecord,
    ProjectGovernanceState,
    ReleaseGateRecord,
    ReleaseRecord,
    ServiceRecord,
    TestRecord,
)
from app.models.entities import (
    Decision,
    DecisionStatus,
    Project,
    ProjectStatus,
    Task,
    WorkStatus,
)
from app.models.holding_evidence import SecurityFinding

HUMAN_BLOCKER_TYPES = {"CREDENTIAL", "ACCESS", "PAYMENT", "LEGAL", "HUMAN_DECISION"}
TERMINAL_PROJECT_STATUSES = {
    ProjectStatus.paused,
    ProjectStatus.archived,
    ProjectStatus.discontinued,
}


def task_done_reasons(db: Session, task: Task) -> list[str]:
    reasons: list[str] = []
    if task.evidence_required:
        verified = db.scalar(
            select(func.count())
            .select_from(EvidenceRecord)
            .where(
                EvidenceRecord.task_id == task.id,
                EvidenceRecord.verification_status == "VERIFIED",
            )
        )
        if not verified:
            reasons.append("verified evidence is required")

    if task.test_required:
        statement = (
            select(func.count())
            .select_from(TestRecord)
            .where(
                TestRecord.task_id == task.id,
                TestRecord.result == "PASS",
            )
        )
        if task.commit_sha:
            statement = statement.where(TestRecord.commit_sha == task.commit_sha)
        if not db.scalar(statement):
            reasons.append("passing test evidence is required")

    if task.metadata_json.get("deploy_required"):
        statement = (
            select(func.count())
            .select_from(DeploymentRecord)
            .where(
                DeploymentRecord.project_id == task.project_id,
                DeploymentRecord.status == "HEALTHY",
            )
        )
        if task.deployment_ref:
            statement = statement.where(DeploymentRecord.deployment_ref == task.deployment_ref)
        if not db.scalar(statement):
            reasons.append("healthy deployment is required")

    blockers = db.scalar(
        select(func.count())
        .select_from(BlockerRecord)
        .where(BlockerRecord.task_id == task.id, BlockerRecord.status == "OPEN")
    )
    if blockers:
        reasons.append("task has an open blocker")
    return reasons


def wip_count(db: Session, project_id: UUID, assigned_agent_id: UUID | None) -> int:
    statement = (
        select(func.count())
        .select_from(Task)
        .where(
            Task.project_id == project_id,
            Task.status == WorkStatus.running,
        )
    )
    if assigned_agent_id is not None:
        statement = statement.where(Task.assigned_agent_id == assigned_agent_id)
    return int(db.scalar(statement) or 0)


def release_gate_reasons(db: Session, release: ReleaseRecord) -> list[str]:
    reasons: list[str] = []
    required = {"CODE", "TEST", "SECURITY", "E2E", "DEPLOY", "OPERATIONS"}
    if release.commercial_status in {"SELLABLE", "CUSTOMERS", "SCALING"}:
        required.add("COMMERCIAL")

    gates = list(
        db.scalars(select(ReleaseGateRecord).where(ReleaseGateRecord.release_id == release.id))
    )
    by_type = {gate.gate_type: gate for gate in gates}
    for gate_type in sorted(required):
        gate = by_type.get(gate_type)
        if gate is None:
            reasons.append(f"{gate_type} gate missing")
        elif gate.status not in {"PASS", "WAIVED"}:
            reasons.append(f"{gate_type} gate is {gate.status}")

    open_blockers = db.scalar(
        select(func.count())
        .select_from(BlockerRecord)
        .where(BlockerRecord.release_id == release.id, BlockerRecord.status == "OPEN")
    )
    if open_blockers:
        reasons.append("release has open blockers")

    security_blockers = db.scalar(
        select(func.count())
        .select_from(SecurityFinding)
        .where(
            SecurityFinding.project_id == release.project_id,
            SecurityFinding.severity.in_(["high", "critical"]),
            SecurityFinding.status.in_(["open", "mitigating"]),
        )
    )
    if security_blockers:
        reasons.append("high/critical security findings remain open")

    return reasons


def release_can_advance(db: Session, release: ReleaseRecord, target: str) -> list[str]:
    if target not in {"READY", "RELEASED"}:
        return []
    return release_gate_reasons(db, release)


GATE_EVIDENCE_KINDS: dict[str, tuple[str, ...]] = {
    "CODE": ("COMMIT", "PR", "CI_RUN"),
    "TEST": ("TEST_RESULT", "CI_RUN"),
    "SECURITY": ("TEST_RESULT", "REPORT", "CI_RUN"),
    "E2E": ("E2E_EXECUTION", "TEST_RESULT"),
    "DEPLOY": ("DEPLOYMENT", "ENDPOINT_HEALTH"),
    "OPERATIONS": ("ENDPOINT_HEALTH", "REPORT"),
    "COMMERCIAL": ("REPORT", "ARTIFACT"),
}


def verify_gate_has_evidence(db: Session, gate: ReleaseGateRecord) -> bool:
    if not gate.evidence_required:
        return True
    accepted_kinds = GATE_EVIDENCE_KINDS.get(gate.gate_type, ())
    return bool(
        db.scalar(
            select(func.count())
            .select_from(EvidenceRecord)
            .where(
                EvidenceRecord.release_id == gate.release_id,
                EvidenceRecord.verification_status == "VERIFIED",
                EvidenceRecord.kind.in_(accepted_kinds),
            )
        )
    )


def _next_best_action(db: Session, project: Project, release: ReleaseRecord | None) -> str | None:
    blocker = db.scalar(
        select(BlockerRecord)
        .where(BlockerRecord.project_id == project.id, BlockerRecord.status == "OPEN")
        .order_by(BlockerRecord.priority, BlockerRecord.created_at)
        .limit(1)
    )
    if blocker is not None:
        return blocker.action_required

    if release is not None:
        failed_gate = db.scalar(
            select(ReleaseGateRecord)
            .where(
                ReleaseGateRecord.release_id == release.id,
                ReleaseGateRecord.status.in_(["FAIL", "NOT_STARTED"]),
            )
            .order_by(ReleaseGateRecord.gate_type)
            .limit(1)
        )
        if failed_gate is not None:
            return f"Close {failed_gate.gate_type} gate for {release.name}"

    task = db.scalar(
        select(Task)
        .where(
            Task.project_id == project.id,
            Task.status.in_([WorkStatus.ready, WorkStatus.planned, WorkStatus.blocked]),
        )
        .order_by(Task.priority, Task.created_at)
        .limit(1)
    )
    if task is not None:
        return task.title
    return None


def recompute_project_governance(
    db: Session,
    project: Project,
    *,
    stale_after_days: int = 3,
) -> ProjectGovernanceState:
    state = db.get(ProjectGovernanceState, project.id)
    if state is None:
        declared_status = (
            "PAUSED" if project.status == ProjectStatus.incubating else project.status.value.upper()
        )
        state = ProjectGovernanceState(
            project_id=project.id,
            declared_status=declared_status,
            verified_status="UNKNOWN",
            priority_tier=f"P{min(project.priority, 3)}",
            health_status="UNKNOWN",
            cost_status="NORMAL",
            commercial_status="NOT_READY",
            monthly_budget_micros=0,
        )
        db.add(state)
        db.flush()

    release = db.get(ReleaseRecord, state.current_release_id) if state.current_release_id else None
    open_blockers = int(
        db.scalar(
            select(func.count())
            .select_from(BlockerRecord)
            .where(BlockerRecord.project_id == project.id, BlockerRecord.status == "OPEN")
        )
        or 0
    )
    unhealthy_services = int(
        db.scalar(
            select(func.count())
            .select_from(ServiceRecord)
            .where(
                ServiceRecord.project_id == project.id,
                ServiceRecord.status.in_(["DEGRADED", "UNHEALTHY"]),
            )
        )
        or 0
    )
    wip = wip_count(db, project.id, None)

    if project.status in TERMINAL_PROJECT_STATUSES:
        state.verified_status = "BLOCKED" if project.status == ProjectStatus.paused else "NOT_DONE"
    elif open_blockers:
        state.verified_status = "BLOCKED"
    elif release and release.status == "RELEASED":
        state.verified_status = "RELEASED"
    elif release and release.status == "READY":
        state.verified_status = "READY"
    elif release and release.status == "FAILED":
        state.verified_status = "FAILED"
    else:
        state.verified_status = "NOT_DONE"

    if unhealthy_services:
        state.health_status = (
            "UNHEALTHY"
            if db.scalar(
                select(func.count())
                .select_from(ServiceRecord)
                .where(ServiceRecord.project_id == project.id, ServiceRecord.status == "UNHEALTHY")
            )
            else "DEGRADED"
        )
    else:
        state.health_status = "HEALTHY"

    latest_task_activity = db.scalar(
        select(func.max(Task.updated_at)).where(Task.project_id == project.id)
    )
    state.last_activity = latest_task_activity or project.updated_at
    cutoff = datetime.now(UTC) - timedelta(days=stale_after_days)
    state.stalled = bool(
        project.status == ProjectStatus.active
        and state.last_activity is not None
        and state.last_activity < cutoff
    )

    state.execution_risk = bool(
        (state.declared_status == "DONE" and state.verified_status not in {"READY", "RELEASED"})
        or wip > 3
        or (release is not None and release.status in {"FAILED", "BLOCKED"})
    )

    p0_blocker = db.scalar(
        select(BlockerRecord)
        .where(
            BlockerRecord.project_id == project.id,
            BlockerRecord.status == "OPEN",
            BlockerRecord.priority == "P0",
        )
        .order_by(BlockerRecord.created_at)
        .limit(1)
    )
    state.scope_creep = False
    if p0_blocker is not None:
        state.scope_creep = bool(
            db.scalar(
                select(func.count())
                .select_from(Task)
                .where(
                    Task.project_id == project.id,
                    Task.priority >= 2,
                    Task.status == WorkStatus.running,
                    Task.created_at > p0_blocker.created_at,
                )
            )
        )

    state.next_best_action = _next_best_action(db, project, release)
    if state.last_verified_activity is None and state.verified_status in {"READY", "RELEASED"}:
        state.last_verified_activity = datetime.now(UTC)
    return state


def human_action_count(db: Session) -> int:
    blockers = int(
        db.scalar(
            select(func.count())
            .select_from(BlockerRecord)
            .where(
                BlockerRecord.status == "OPEN",
                BlockerRecord.blocker_type.in_(sorted(HUMAN_BLOCKER_TYPES)),
            )
        )
        or 0
    )
    decisions = int(
        db.scalar(
            select(func.count())
            .select_from(Decision)
            .where(Decision.status == DecisionStatus.pending, Decision.requires_human.is_(True))
        )
        or 0
    )
    return blockers + decisions


def human_actions(db: Session) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for blocker in db.scalars(
        select(BlockerRecord)
        .where(
            BlockerRecord.status == "OPEN",
            BlockerRecord.blocker_type.in_(sorted(HUMAN_BLOCKER_TYPES)),
        )
        .order_by(BlockerRecord.priority, BlockerRecord.created_at)
    ):
        rows.append(
            {
                "kind": "BLOCKER",
                "id": str(blocker.id),
                "project_id": str(blocker.project_id),
                "priority": blocker.priority,
                "title": blocker.description,
                "action_required": blocker.action_required,
                "owner": blocker.owner,
            }
        )
    for decision in db.scalars(
        select(Decision)
        .where(Decision.status == DecisionStatus.pending, Decision.requires_human.is_(True))
        .order_by(Decision.created_at)
    ):
        rows.append(
            {
                "kind": "DECISION",
                "id": str(decision.id),
                "project_id": str(decision.project_id),
                "priority": "P0" if decision.risk_level.value in {"high", "critical"} else "P1",
                "title": decision.title,
                "action_required": decision.recommendation or "Owner decision required",
                "owner": "OWNER",
            }
        )
    return rows


def owner_view(db: Session) -> dict[str, object]:
    projects = list(db.scalars(select(Project).order_by(Project.priority, Project.name)))
    project_rows: list[dict[str, object]] = []
    releases_at_risk = 0
    sellable = 0
    blocked_projects = 0

    for project in projects:
        state = recompute_project_governance(db, project)
        release = (
            db.get(ReleaseRecord, state.current_release_id) if state.current_release_id else None
        )
        blockers = int(
            db.scalar(
                select(func.count())
                .select_from(BlockerRecord)
                .where(BlockerRecord.project_id == project.id, BlockerRecord.status == "OPEN")
            )
            or 0
        )
        wip = wip_count(db, project.id, None)
        if blockers or state.verified_status == "BLOCKED":
            blocked_projects += 1
        if release is not None and release.status in {"BLOCKED", "FAILED"}:
            releases_at_risk += 1
        if state.commercial_status in {"SELLABLE", "CUSTOMERS", "SCALING"}:
            sellable += 1
        project_rows.append(
            {
                "project_id": project.id,
                "key": project.key,
                "name": project.name,
                "project_status": project.status.value.upper(),
                "declared_status": state.declared_status,
                "verified_status": state.verified_status,
                "priority_tier": state.priority_tier,
                "health_status": state.health_status,
                "commercial_status": state.commercial_status,
                "cost_status": state.cost_status,
                "current_release": release.name if release else None,
                "next_best_action": state.next_best_action,
                "open_blockers": blockers,
                "wip": wip,
                "stalled": state.stalled,
                "execution_risk": state.execution_risk,
                "scope_creep": state.scope_creep,
            }
        )

    db.flush()
    return {
        "projects": project_rows,
        "active_projects": sum(p.status == ProjectStatus.active for p in projects),
        "paused_projects": sum(p.status == ProjectStatus.paused for p in projects),
        "blocked_projects": blocked_projects,
        "sellable_products": sellable,
        "releases_at_risk": releases_at_risk,
        "human_actions": human_action_count(db),
        "unhealthy_services": int(
            db.scalar(
                select(func.count())
                .select_from(ServiceRecord)
                .where(ServiceRecord.status.in_(["DEGRADED", "UNHEALTHY"]))
            )
            or 0
        ),
    }
