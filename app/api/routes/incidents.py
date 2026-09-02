from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.db.session import get_db
from app.models.entities import Incident, IncidentStatus, Project
from app.schemas.operations import IncidentCreate, IncidentOut, IncidentTransition
from app.services.audit import record_audit

router = APIRouter(prefix="/incidents", tags=["incidents"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]

ALLOWED_TRANSITIONS: dict[IncidentStatus, set[IncidentStatus]] = {
    IncidentStatus.open: {
        IncidentStatus.investigating,
        IncidentStatus.mitigated,
        IncidentStatus.resolved,
    },
    IncidentStatus.investigating: {IncidentStatus.mitigated, IncidentStatus.resolved},
    IncidentStatus.mitigated: {IncidentStatus.investigating, IncidentStatus.resolved},
    IncidentStatus.resolved: set(),
}


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    db: DbSession,
    incident_status: IncidentStatus | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Incident]:
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    statement = select(Incident)
    if incident_status:
        statement = statement.where(Incident.status == incident_status)
    statement = statement.order_by(Incident.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement))


@router.post("", response_model=IncidentOut, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: DbSession, actor: Actor) -> Incident:
    if payload.project_id and not db.get(Project, payload.project_id):
        raise HTTPException(status_code=400, detail="project not found")

    incident = Incident(**payload.model_dump())
    db.add(incident)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="incident.created",
        entity_type="incident",
        entity_id=str(incident.id),
        payload={"severity": incident.severity.value, "source": incident.source},
    )
    db.commit()
    db.refresh(incident)
    return incident


@router.post("/{incident_id}/transition", response_model=IncidentOut)
def transition_incident(
    incident_id: UUID,
    payload: IncidentTransition,
    db: DbSession,
    actor: Actor,
) -> Incident:
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")
    if payload.status not in ALLOWED_TRANSITIONS[incident.status]:
        raise HTTPException(
            status_code=409,
            detail=f"invalid transition {incident.status.value} -> {payload.status.value}",
        )

    old_status = incident.status
    incident.status = payload.status
    if payload.root_cause is not None:
        incident.root_cause = payload.root_cause
    if payload.status == IncidentStatus.resolved:
        incident.resolution = payload.resolution
        incident.resolved_at = datetime.now(UTC)

    record_audit(
        db,
        actor=actor,
        action="incident.transitioned",
        entity_type="incident",
        entity_id=str(incident.id),
        payload={"from": old_status.value, "to": incident.status.value},
    )
    db.commit()
    db.refresh(incident)
    return incident
