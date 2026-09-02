from datetime import UTC, datetime
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.db.session import get_db
from app.models.entities import AcceptanceCriterion, CriterionStatus, Milestone, Project
from app.schemas.api import (
    CriterionCreate,
    CriterionOut,
    CriterionVerify,
    MilestoneCreate,
    MilestoneOut,
    ProjectCreate,
    ProjectOut,
    ProjectProgress,
)
from app.services.audit import record_audit
from app.services.progress import project_progress

router = APIRouter(prefix="/projects", tags=["projects"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: DbSession,
    limit: int = 100,
    offset: int = 0,
) -> list[Project]:
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    statement = select(Project).order_by(Project.priority, Project.name).limit(limit).offset(offset)
    return list(db.scalars(statement))


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: DbSession,
    actor: Actor,
) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="project already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="project.created",
        entity_type="project",
        entity_id=str(project.id),
    )
    db.commit()
    db.refresh(project)
    return project


@router.post(
    "/{project_id}/milestones",
    response_model=MilestoneOut,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    project_id: UUID,
    payload: MilestoneCreate,
    db: DbSession,
    actor: Actor,
) -> Milestone:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    milestone = Milestone(project_id=project.id, **payload.model_dump())
    db.add(milestone)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="milestone key already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="milestone.created",
        entity_type="milestone",
        entity_id=str(milestone.id),
        payload={"project_id": str(project.id)},
    )
    db.commit()
    db.refresh(milestone)
    return milestone


@router.post(
    "/{project_id}/milestones/{milestone_id}/criteria",
    response_model=CriterionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_criterion(
    project_id: UUID,
    milestone_id: UUID,
    payload: CriterionCreate,
    db: DbSession,
    actor: Actor,
) -> AcceptanceCriterion:
    milestone = db.get(Milestone, milestone_id)
    if not milestone or milestone.project_id != project_id:
        raise HTTPException(status_code=404, detail="milestone not found in project")
    criterion = AcceptanceCriterion(milestone_id=milestone.id, **payload.model_dump())
    db.add(criterion)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="criterion key already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="criterion.created",
        entity_type="acceptance_criterion",
        entity_id=str(criterion.id),
    )
    db.commit()
    db.refresh(criterion)
    return criterion


@router.post(
    "/{project_id}/milestones/{milestone_id}/criteria/{criterion_id}/verify",
    response_model=CriterionOut,
)
def verify_criterion(
    project_id: UUID,
    milestone_id: UUID,
    criterion_id: UUID,
    payload: CriterionVerify,
    db: DbSession,
    actor: Actor,
) -> AcceptanceCriterion:
    milestone = db.get(Milestone, milestone_id)
    criterion = db.get(AcceptanceCriterion, criterion_id)
    if (
        not milestone
        or milestone.project_id != project_id
        or not criterion
        or criterion.milestone_id != milestone.id
    ):
        raise HTTPException(status_code=404, detail="criterion not found in milestone")
    criterion.status = CriterionStatus.verified
    criterion.verifier = actor.name
    criterion.evidence = cast(list[object], payload.evidence)
    criterion.verified_at = datetime.now(UTC)
    record_audit(
        db,
        actor=actor,
        action="criterion.verified",
        entity_type="acceptance_criterion",
        entity_id=str(criterion.id),
        payload={"evidence_count": len(payload.evidence)},
    )
    db.commit()
    db.refresh(criterion)
    return criterion


@router.get("/{project_id}/progress", response_model=ProjectProgress)
def get_project_progress(project_id: UUID, db: DbSession) -> ProjectProgress:
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="project not found")
    return project_progress(db, project_id)
