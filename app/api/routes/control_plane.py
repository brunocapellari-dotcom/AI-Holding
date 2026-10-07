from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
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
from app.models.entities import Project, Task
from app.schemas.control_plane import (
    BlockerCreate,
    BlockerOut,
    DeploymentCreate,
    DeploymentOut,
    EvidenceCreate,
    EvidenceOut,
    EvidenceVerify,
    GateOut,
    GateUpsert,
    GovernanceOut,
    GovernanceUpsert,
    OwnerView,
    ReleaseCreate,
    ReleaseOut,
    ReleaseStatusUpdate,
    ServiceOut,
    ServiceUpsert,
    TestCreate,
    TestOut,
)
from app.services.audit import record_audit
from app.services.control_plane import (
    human_actions,
    owner_view,
    recompute_project_governance,
    release_can_advance,
    verify_gate_has_evidence,
)

router = APIRouter(prefix="/holding/control-plane", tags=["control-plane"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def _record_permission(db: Session, actor: ActorContext) -> None:
    authorize_mutation(db, actor, permission=AgentPermission.record_operational_state)


@router.get("/owner-view", response_model=OwnerView)
def get_owner_view(db: DbSession) -> OwnerView:
    result = OwnerView.model_validate(owner_view(db))
    db.commit()
    return result


@router.get("/human-actions")
def get_human_actions(db: DbSession) -> list[dict[str, object]]:
    return human_actions(db)


@router.put("/projects/{project_id}/governance", response_model=GovernanceOut)
def upsert_governance(
    project_id: UUID, payload: GovernanceUpsert, db: DbSession, actor: Actor
) -> ProjectGovernanceState:
    authorize_mutation(db, actor)
    project = _project(db, project_id)
    if payload.current_release_id:
        release = db.get(ReleaseRecord, payload.current_release_id)
        if release is None or release.project_id != project.id:
            raise HTTPException(
                status_code=400,
                detail="current release does not belong to project",
            )
    state = db.get(ProjectGovernanceState, project.id)
    if state is None:
        state = ProjectGovernanceState(project_id=project.id)
        db.add(state)
    for key, value in payload.model_dump().items():
        setattr(state, key, value)
    db.flush()
    recompute_project_governance(db, project)
    record_audit(
        db,
        actor=actor,
        action="project.governance.updated",
        entity_type="project_governance_state",
        entity_id=str(project.id),
        payload={"declared_status": state.declared_status, "priority_tier": state.priority_tier},
    )
    db.commit()
    db.refresh(state)
    return state


@router.post("/releases", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
def create_release(payload: ReleaseCreate, db: DbSession, actor: Actor) -> ReleaseRecord:
    authorize_mutation(db, actor)
    _project(db, payload.project_id)
    release = ReleaseRecord(**payload.model_dump())
    db.add(release)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="release already exists") from exc
    for gate_type in ("CODE", "TEST", "SECURITY", "E2E", "DEPLOY", "OPERATIONS"):
        db.add(ReleaseGateRecord(release_id=release.id, gate_type=gate_type))
    record_audit(
        db,
        actor=actor,
        action="release.created",
        entity_type="release",
        entity_id=str(release.id),
        payload={"project_id": str(release.project_id), "name": release.name},
    )
    db.commit()
    db.refresh(release)
    return release


@router.get("/releases", response_model=list[ReleaseOut])
def list_releases(db: DbSession, project_id: UUID | None = None) -> list[ReleaseRecord]:
    statement = select(ReleaseRecord).order_by(ReleaseRecord.created_at.desc())
    if project_id:
        statement = statement.where(ReleaseRecord.project_id == project_id)
    return list(db.scalars(statement))


@router.post("/releases/{release_id}/status", response_model=ReleaseOut)
def update_release_status(
    release_id: UUID, payload: ReleaseStatusUpdate, db: DbSession, actor: Actor
) -> ReleaseRecord:
    authorize_mutation(db, actor)
    release = db.get(ReleaseRecord, release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="release not found")
    if payload.commercial_status is not None:
        release.commercial_status = payload.commercial_status
    reasons = release_can_advance(db, release, payload.status)
    if (
        payload.commercial_status in {"SELLABLE", "CUSTOMERS", "SCALING"}
        and payload.status not in {"READY", "RELEASED"}
    ):
        reasons = release_can_advance(db, release, "READY")
    if reasons:
        raise HTTPException(
            status_code=409,
            detail={"message": "release gate rejected", "reasons": reasons},
        )
    release.status = payload.status
    state = db.get(ProjectGovernanceState, release.project_id)
    if state is not None and state.current_release_id == release.id:
        state.commercial_status = release.commercial_status
    record_audit(
        db,
        actor=actor,
        action="release.status.updated",
        entity_type="release",
        entity_id=str(release.id),
        payload={"status": release.status, "commercial_status": release.commercial_status},
    )
    db.commit()
    db.refresh(release)
    return release


@router.get("/releases/{release_id}/gates", response_model=list[GateOut])
def list_release_gates(release_id: UUID, db: DbSession) -> list[ReleaseGateRecord]:
    if db.get(ReleaseRecord, release_id) is None:
        raise HTTPException(status_code=404, detail="release not found")
    return list(
        db.scalars(
            select(ReleaseGateRecord)
            .where(ReleaseGateRecord.release_id == release_id)
            .order_by(ReleaseGateRecord.gate_type)
        )
    )


@router.put("/releases/{release_id}/gates/{gate_type}", response_model=GateOut)
def upsert_release_gate(
    release_id: UUID,
    gate_type: str,
    payload: GateUpsert,
    db: DbSession,
    actor: Actor,
) -> ReleaseGateRecord:
    authorize_mutation(db, actor, permission=AgentPermission.verify_operational_evidence)
    if payload.gate_type != gate_type:
        raise HTTPException(status_code=400, detail="gate type mismatch")
    if db.get(ReleaseRecord, release_id) is None:
        raise HTTPException(status_code=404, detail="release not found")
    gate = db.scalar(
        select(ReleaseGateRecord).where(
            ReleaseGateRecord.release_id == release_id,
            ReleaseGateRecord.gate_type == gate_type,
        )
    )
    if gate is None:
        gate = ReleaseGateRecord(release_id=release_id, gate_type=gate_type)
        db.add(gate)
        db.flush()
    gate.status = payload.status
    gate.evidence_required = payload.evidence_required
    gate.notes = payload.notes
    if payload.status == "PASS":
        if not verify_gate_has_evidence(db, gate):
            raise HTTPException(status_code=409, detail="verified release evidence is required")
        gate.verified_at = datetime.now(UTC)
    else:
        gate.verified_at = None
    db.commit()
    db.refresh(gate)
    return gate


@router.post("/evidence", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
def create_evidence(payload: EvidenceCreate, db: DbSession, actor: Actor) -> EvidenceRecord:
    _record_permission(db, actor)
    if payload.project_id:
        _project(db, payload.project_id)
    if payload.task_id and db.get(Task, payload.task_id) is None:
        raise HTTPException(status_code=404, detail="task not found")
    if payload.release_id and db.get(ReleaseRecord, payload.release_id) is None:
        raise HTTPException(status_code=404, detail="release not found")
    evidence = EvidenceRecord(**payload.model_dump())
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.post("/evidence/{evidence_id}/verify", response_model=EvidenceOut)
def verify_evidence(
    evidence_id: UUID, payload: EvidenceVerify, db: DbSession, actor: Actor
) -> EvidenceRecord:
    authorize_mutation(db, actor, permission=AgentPermission.verify_operational_evidence)
    evidence = db.get(EvidenceRecord, evidence_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="evidence not found")
    evidence.verification_status = payload.verification_status
    evidence.verified_at = datetime.now(UTC)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.put("/services", response_model=ServiceOut)
def upsert_service(payload: ServiceUpsert, db: DbSession, actor: Actor) -> ServiceRecord:
    _record_permission(db, actor)
    _project(db, payload.project_id)
    service = db.scalar(
        select(ServiceRecord).where(
            ServiceRecord.project_id == payload.project_id,
            ServiceRecord.name == payload.name,
            ServiceRecord.environment == payload.environment,
        )
    )
    if service is None:
        service = ServiceRecord(**payload.model_dump())
        db.add(service)
    else:
        for key, value in payload.model_dump().items():
            setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return service


@router.post("/deployments", response_model=DeploymentOut, status_code=status.HTTP_201_CREATED)
def create_deployment(payload: DeploymentCreate, db: DbSession, actor: Actor) -> DeploymentRecord:
    _record_permission(db, actor)
    _project(db, payload.project_id)
    deployment = DeploymentRecord(**payload.model_dump())
    db.add(deployment)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="deployment reference already exists") from exc
    db.refresh(deployment)
    return deployment


@router.post("/tests", response_model=TestOut, status_code=status.HTTP_201_CREATED)
def create_test(payload: TestCreate, db: DbSession, actor: Actor) -> TestRecord:
    _record_permission(db, actor)
    _project(db, payload.project_id)
    test = TestRecord(**payload.model_dump())
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.post("/blockers", response_model=BlockerOut, status_code=status.HTTP_201_CREATED)
def create_blocker(payload: BlockerCreate, db: DbSession, actor: Actor) -> BlockerRecord:
    _record_permission(db, actor)
    _project(db, payload.project_id)
    blocker = BlockerRecord(**payload.model_dump())
    db.add(blocker)
    db.commit()
    db.refresh(blocker)
    return blocker


@router.post("/blockers/{blocker_id}/resolve", response_model=BlockerOut)
def resolve_blocker(blocker_id: UUID, db: DbSession, actor: Actor) -> BlockerRecord:
    _record_permission(db, actor)
    blocker = db.get(BlockerRecord, blocker_id)
    if blocker is None:
        raise HTTPException(status_code=404, detail="blocker not found")
    blocker.status = "RESOLVED"
    blocker.resolved_at = datetime.now(UTC)
    db.commit()
    db.refresh(blocker)
    return blocker


@router.post("/projects/{project_id}/recompute", response_model=GovernanceOut)
def recompute_project(
    project_id: UUID, db: DbSession, actor: Actor
) -> ProjectGovernanceState:
    _record_permission(db, actor)
    project = _project(db, project_id)
    state = recompute_project_governance(db, project)
    db.commit()
    db.refresh(state)
    return state
