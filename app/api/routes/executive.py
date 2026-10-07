from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.release_control import load_release_manifest
from app.models.entities import (
    Decision,
    DecisionStatus,
    Incident,
    IncidentStatus,
    Project,
    ProjectStatus,
    Task,
    WorkStatus,
)
from app.schemas.api import ExecutiveSummary
from app.services.progress import project_progress

router = APIRouter(prefix="/executive", tags=["executive"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/summary", response_model=ExecutiveSummary)
def executive_summary(db: DbSession) -> ExecutiveSummary:
    def count(stmt: Any) -> int:
        return int(db.scalar(stmt) or 0)

    active_project_stmt = (
        select(Project).where(Project.status == ProjectStatus.active).order_by(Project.key)
    )
    active_projects = list(db.scalars(active_project_stmt))
    progresses = [project_progress(db, project.id).progress_pct for project in active_projects]
    portfolio_progress = round(sum(progresses) / len(progresses), 2) if progresses else 0.0

    running_tasks = count(
        select(func.count()).select_from(Task).where(Task.status == WorkStatus.running)
    )
    blocked_tasks = count(
        select(func.count()).select_from(Task).where(Task.status == WorkStatus.blocked)
    )
    pending_human_decisions = count(
        select(func.count())
        .select_from(Decision)
        .where(
            Decision.status == DecisionStatus.pending,
            Decision.requires_human.is_(True),
        )
    )
    open_incidents = count(
        select(func.count())
        .select_from(Incident)
        .where(Incident.status.in_([IncidentStatus.open, IncidentStatus.investigating]))
    )

    return ExecutiveSummary(
        active_projects=len(active_projects),
        running_tasks=running_tasks,
        blocked_tasks=blocked_tasks,
        pending_human_decisions=pending_human_decisions,
        open_incidents=open_incidents,
        portfolio_progress_pct=portfolio_progress,
    )


@router.get("/releases/agrolog-commercial-2026-10-09")
def agrolog_commercial_release() -> dict[str, object]:
    release = load_release_manifest()
    return {
        "initiative": release.initiative,
        "product": release.product,
        "target_date": release.target_date,
        "release_status": release.release_status.value,
        "completed": release.completed,
        "p2_frozen": release.p2_frozen,
        "missing_gate_evidence": sorted(release.missing_gate_evidence),
        "commercial_test": release.commercial_test.model_dump(mode="json"),
        "dashboard": release.dashboard(),
    }
