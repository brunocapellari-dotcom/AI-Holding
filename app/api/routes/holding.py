from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.actor import ActorContext, get_actor
from app.core.authorization import authorize_mutation
from app.db.session import get_db
from app.models.entities import Project
from app.models.holding import (
    CollectorRegistration,
    CostEntry,
    DependencyEdge,
    HoldingAlert,
    IntegrationState,
    ProjectOperationalProfile,
    RiskRegisterEntry,
    VentureEvaluation,
)
from app.schemas.holding import (
    AlertCreate,
    AlertOut,
    CollectorOut,
    CollectorUpsert,
    CostCreate,
    CostOut,
    CostSummary,
    DependencyCreate,
    DependencyOut,
    ExecutiveStateOut,
    HealthOut,
    IntegrationOut,
    IntegrationUpsert,
    OperationalProfileOut,
    OperationalProfileUpsert,
    ProjectContractOut,
    RiskCreate,
    RiskOut,
    VentureCreate,
    VentureOut,
)
from app.services.audit import record_audit
from app.services.holding import (
    compute_project_health,
    executive_state,
    project_contract,
    summarize_costs,
)

router = APIRouter(prefix="/holding", tags=["holding"])
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _require_project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.put("/projects/{project_id}/profile", response_model=OperationalProfileOut)
def upsert_project_profile(
    project_id: UUID,
    payload: OperationalProfileUpsert,
    db: DbSession,
    actor: Actor,
) -> ProjectOperationalProfile:
    authorize_mutation(db, actor)
    _require_project(db, project_id)
    profile = db.get(ProjectOperationalProfile, project_id)
    if profile is None:
        profile = ProjectOperationalProfile(project_id=project_id, **payload.model_dump())
        db.add(profile)
        action = "project_operational_profile.created"
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
        action = "project_operational_profile.updated"
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="project_operational_profile",
        entity_id=str(project_id),
        payload={"operational_status": profile.operational_status},
    )
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/projects/{project_id}/contract", response_model=ProjectContractOut)
def get_project_contract(project_id: UUID, db: DbSession) -> ProjectContractOut:
    try:
        return project_contract(db, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="project not found") from exc


@router.post("/projects/{project_id}/health/recompute", response_model=HealthOut)
def recompute_health(project_id: UUID, db: DbSession, actor: Actor) -> HealthOut:
    authorize_mutation(db, actor)
    _require_project(db, project_id)
    result = compute_project_health(db, project_id, persist=True)
    record_audit(
        db,
        actor=actor,
        action="project_health.recomputed",
        entity_type="project",
        entity_id=str(project_id),
        payload={"state": result.state, "score": result.score},
    )
    db.commit()
    return result


@router.put("/projects/{project_id}/collectors/{collector_key}", response_model=CollectorOut)
def upsert_collector(
    project_id: UUID,
    collector_key: str,
    payload: CollectorUpsert,
    db: DbSession,
    actor: Actor,
) -> CollectorRegistration:
    authorize_mutation(db, actor)
    _require_project(db, project_id)
    if payload.key != collector_key:
        raise HTTPException(status_code=400, detail="collector key mismatch")
    collector = db.scalar(
        select(CollectorRegistration).where(
            CollectorRegistration.project_id == project_id,
            CollectorRegistration.key == collector_key,
        )
    )
    if collector is None:
        collector = CollectorRegistration(project_id=project_id, **payload.model_dump())
        db.add(collector)
        action = "collector.created"
    else:
        for key, value in payload.model_dump().items():
            setattr(collector, key, value)
        action = "collector.updated"
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="collector",
        entity_id=collector_key,
        payload={"project_id": str(project_id), "status": collector.status},
    )
    db.commit()
    db.refresh(collector)
    return collector


@router.get("/projects/{project_id}/collectors", response_model=list[CollectorOut])
def list_collectors(project_id: UUID, db: DbSession) -> list[CollectorRegistration]:
    _require_project(db, project_id)
    return list(
        db.scalars(
            select(CollectorRegistration)
            .where(CollectorRegistration.project_id == project_id)
            .order_by(CollectorRegistration.key)
        )
    )


@router.post("/risks", response_model=RiskOut, status_code=status.HTTP_201_CREATED)
def create_risk(payload: RiskCreate, db: DbSession, actor: Actor) -> RiskRegisterEntry:
    authorize_mutation(db, actor)
    if payload.project_id is not None:
        _require_project(db, payload.project_id)
    risk = RiskRegisterEntry(**payload.model_dump())
    db.add(risk)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="risk already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="risk.created",
        entity_type="risk",
        entity_id=str(risk.id),
        payload={"key": risk.key, "severity": risk.severity},
    )
    db.commit()
    db.refresh(risk)
    return risk


@router.get("/risks", response_model=list[RiskOut])
def list_risks(db: DbSession, project_id: UUID | None = None) -> list[RiskRegisterEntry]:
    statement = select(RiskRegisterEntry).order_by(
        RiskRegisterEntry.severity.desc(), RiskRegisterEntry.date_detected.desc()
    )
    if project_id is not None:
        statement = statement.where(RiskRegisterEntry.project_id == project_id)
    return list(db.scalars(statement))


@router.post("/costs", response_model=CostOut, status_code=status.HTTP_201_CREATED)
def create_cost(payload: CostCreate, db: DbSession, actor: Actor) -> CostEntry:
    authorize_mutation(db, actor)
    if payload.project_id is not None:
        _require_project(db, payload.project_id)
    cost = CostEntry(**payload.model_dump())
    db.add(cost)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="cost.recorded",
        entity_type="cost_entry",
        entity_id=str(cost.id),
        payload={"provider": cost.provider, "category": cost.category},
    )
    db.commit()
    db.refresh(cost)
    return cost


@router.get("/costs/summary", response_model=CostSummary)
def get_cost_summary(db: DbSession, project_id: UUID | None = None) -> CostSummary:
    if project_id is not None:
        _require_project(db, project_id)
    return summarize_costs(db, project_id)


@router.post("/dependencies", response_model=DependencyOut, status_code=status.HTTP_201_CREATED)
def create_dependency(payload: DependencyCreate, db: DbSession, actor: Actor) -> DependencyEdge:
    authorize_mutation(db, actor)
    dependency = DependencyEdge(**payload.model_dump())
    db.add(dependency)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="dependency already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="dependency.created",
        entity_type="dependency_edge",
        entity_id=str(dependency.id),
        payload={
            "source": f"{dependency.source_type}:{dependency.source_key}",
            "target": f"{dependency.target_type}:{dependency.target_key}",
        },
    )
    db.commit()
    db.refresh(dependency)
    return dependency


@router.get("/dependencies", response_model=list[DependencyOut])
def list_dependencies(db: DbSession) -> list[DependencyEdge]:
    return list(
        db.scalars(
            select(DependencyEdge).order_by(
                DependencyEdge.source_type,
                DependencyEdge.source_key,
                DependencyEdge.target_type,
                DependencyEdge.target_key,
            )
        )
    )


@router.post("/alerts", response_model=AlertOut)
def upsert_alert(payload: AlertCreate, db: DbSession, actor: Actor) -> HoldingAlert:
    authorize_mutation(db, actor)
    if payload.project_id is not None:
        _require_project(db, payload.project_id)
    alert = db.scalar(select(HoldingAlert).where(HoldingAlert.dedupe_key == payload.dedupe_key))
    now = datetime.now(UTC)
    if alert is None:
        alert = HoldingAlert(**payload.model_dump(), last_seen_at=now)
        db.add(alert)
        action = "alert.created"
    else:
        alert.project_id = payload.project_id
        alert.level = payload.level
        alert.source = payload.source
        alert.title = payload.title
        alert.details = payload.details
        alert.status = payload.status
        alert.occurrences += 1
        alert.last_seen_at = now
        action = "alert.updated"
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="holding_alert",
        entity_id=str(alert.id),
        payload={"level": alert.level, "dedupe_key": alert.dedupe_key},
    )
    db.commit()
    db.refresh(alert)
    return alert


@router.put("/integrations/{service_key}", response_model=IntegrationOut)
def upsert_integration(
    service_key: str,
    payload: IntegrationUpsert,
    db: DbSession,
    actor: Actor,
) -> IntegrationState:
    authorize_mutation(db, actor)
    if payload.service_key != service_key:
        raise HTTPException(status_code=400, detail="integration service key mismatch")
    integration = db.scalar(
        select(IntegrationState).where(IntegrationState.service_key == service_key)
    )
    if integration is None:
        integration = IntegrationState(**payload.model_dump())
        db.add(integration)
        action = "integration.created"
    else:
        for key, value in payload.model_dump().items():
            setattr(integration, key, value)
        action = "integration.updated"
    db.flush()
    record_audit(
        db,
        actor=actor,
        action=action,
        entity_type="integration_state",
        entity_id=str(integration.id),
        payload={"service_key": service_key, "status": integration.status},
    )
    db.commit()
    db.refresh(integration)
    return integration


@router.get("/integrations", response_model=list[IntegrationOut])
def list_integrations(db: DbSession) -> list[IntegrationState]:
    return list(db.scalars(select(IntegrationState).order_by(IntegrationState.service_key)))


@router.post("/ventures", response_model=VentureOut, status_code=status.HTTP_201_CREATED)
def create_venture(payload: VentureCreate, db: DbSession, actor: Actor) -> VentureEvaluation:
    authorize_mutation(db, actor)
    venture = VentureEvaluation(**payload.model_dump())
    db.add(venture)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="venture already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="venture.created",
        entity_type="venture_evaluation",
        entity_id=str(venture.id),
        payload={"key": venture.key, "decision": venture.decision},
    )
    db.commit()
    db.refresh(venture)
    return venture


@router.get("/ventures", response_model=list[VentureOut])
def list_ventures(db: DbSession) -> list[VentureEvaluation]:
    return list(db.scalars(select(VentureEvaluation).order_by(VentureEvaluation.created_at.desc())))


@router.get("/executive-state", response_model=ExecutiveStateOut)
def get_executive_state(db: DbSession) -> ExecutiveStateOut:
    return executive_state(db)
