from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import authorize_mutation
from app.db.session import get_db
from app.models.entities import Project
from app.models.holding_governance import CapabilityAutonomy
from app.schemas.holding_governance import (
    CapabilityAutonomyOut,
    CapabilityAutonomyUpsert,
    GovernanceReviewOut,
)
from app.services.audit import record_audit
from app.services.governance_review import review_project_governance

router = APIRouter(prefix="/holding/governance", tags=["holding-governance"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _require_project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def _require_human(actor: ActorContext) -> None:
    if actor.actor_type != "human":
        raise HTTPException(
            status_code=403,
            detail="capability autonomy changes require a human owner",
        )


@router.put(
    "/projects/{project_id}/capabilities/{capability_key}",
    response_model=CapabilityAutonomyOut,
)
def upsert_capability_autonomy(
    project_id: UUID,
    capability_key: str,
    payload: CapabilityAutonomyUpsert,
    db: DbSession,
    actor: Actor,
) -> CapabilityAutonomy:
    authorize_mutation(db, actor)
    _require_human(actor)
    _require_project(db, project_id)
    if payload.capability_key != capability_key:
        raise HTTPException(status_code=400, detail="capability key mismatch")
    if payload.autonomy_level >= 4 and not payload.constraints:
        raise HTTPException(
            status_code=422,
            detail="A4/A5 autonomy requires explicit deterministic constraints",
        )
    if payload.autonomy_level >= 4 and not payload.evidence:
        raise HTTPException(
            status_code=422,
            detail="A4/A5 autonomy requires objective evidence",
        )

    entry = db.scalar(
        select(CapabilityAutonomy).where(
            CapabilityAutonomy.project_id == project_id,
            CapabilityAutonomy.capability_key == capability_key,
        )
    )
    values = payload.model_dump()
    if entry is None:
        entry = CapabilityAutonomy(project_id=project_id, **values)
        db.add(entry)
        action = "capability_autonomy.created"
    else:
        for key, value in values.items():
            setattr(entry, key, value)
        action = "capability_autonomy.updated"

    if payload.status == "validated":
        entry.reviewed_by = actor.name
        entry.reviewed_at = datetime.now(UTC)
    else:
        entry.reviewed_by = None
        entry.reviewed_at = None

    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="capability_autonomy",
        entity_id=str(entry.id),
        payload={
            "project_id": str(project_id),
            "capability_key": capability_key,
            "autonomy_level": entry.autonomy_level,
            "status": entry.status,
        },
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get(
    "/projects/{project_id}/capabilities",
    response_model=list[CapabilityAutonomyOut],
)
def list_capability_autonomy(
    project_id: UUID,
    db: DbSession,
) -> list[CapabilityAutonomy]:
    _require_project(db, project_id)
    return list(
        db.scalars(
            select(CapabilityAutonomy)
            .where(CapabilityAutonomy.project_id == project_id)
            .order_by(CapabilityAutonomy.capability_key)
        )
    )


@router.post(
    "/projects/{project_id}/review",
    response_model=GovernanceReviewOut,
)
def review_governance(
    project_id: UUID,
    db: DbSession,
    actor: Actor,
) -> GovernanceReviewOut:
    authorize_mutation(db, actor)
    _require_project(db, project_id)
    result = review_project_governance(db, project_id)
    record_audit(
        db,
        actor=actor,
        action="governance_review.created",
        entity_type="project",
        entity_id=str(project_id),
        payload={"score": result.score, "finding_count": len(result.findings)},
    )
    db.commit()
    return result
