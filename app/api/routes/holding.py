from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.access_dependencies import (
    require_financial_read,
    require_governance_read,
    require_operational_read,
    require_security_read,
)
from app.core.actor import ActorContext, get_actor
from app.core.authorization import AgentPermission, authorize_mutation
from app.db.session import get_db
from app.models.entities import Project
from app.models.holding import (
    CollectorRegistration,
    CostEntry,
    DependencyEdge,
    FinancialSnapshot,
    HoldingAlert,
    IntegrationState,
    PortfolioReview,
    ProjectOperationalProfile,
    ResourceAllocationEntry,
    RevenueEntry,
    RiskRegisterEntry,
    ToolDecision,
    VentureEvaluation,
)
from app.models.holding_evidence import CollectorExecution, SecurityFinding
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
    FinancialSnapshotCreate,
    FinancialSnapshotOut,
    HealthOut,
    IntegrationOut,
    IntegrationUpsert,
    OperationalProfileOut,
    OperationalProfileUpsert,
    PortfolioReviewCreate,
    PortfolioReviewOut,
    ProjectContractOut,
    ProjectRegistryEntryOut,
    ResourceAllocationCreate,
    ResourceAllocationOut,
    RevenueCreate,
    RevenueOut,
    RevenueSummary,
    RiskCreate,
    RiskOut,
    ToolDecisionCreate,
    ToolDecisionOut,
    VentureCreate,
    VentureOut,
)
from app.schemas.holding_analysis import CompletionGateOut, FinOpsAnalysisOut, VentureGateOut
from app.schemas.holding_evidence import (
    CollectorExecutionCreate,
    CollectorExecutionOut,
    SecurityFindingCreate,
    SecurityFindingOut,
)
from app.services.audit import record_audit
from app.services.holding import (
    compute_project_health,
    executive_state,
    project_contract,
    project_registry,
    summarize_costs,
    summarize_revenues,
)
from app.services.holding_analysis import analyze_finops, completion_gate, evaluate_venture

router = APIRouter(
    prefix="/holding",
    tags=["holding"],
    dependencies=[Depends(require_operational_read)],
)
DbSession = Annotated[Session, Depends(get_db)]
Actor = Annotated[ActorContext, Depends(get_actor)]


def _require_project(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


def _require_human(actor: ActorContext, detail: str) -> None:
    if actor.actor_type != "human":
        raise HTTPException(status_code=403, detail=detail)


@router.get("/projects/registry", response_model=list[ProjectRegistryEntryOut])
def get_project_registry(db: DbSession) -> list[ProjectRegistryEntryOut]:
    return project_registry(db)


@router.get("/projects/{project_id}/completion-gate", response_model=CompletionGateOut)
def get_completion_gate(project_id: UUID, db: DbSession) -> CompletionGateOut:
    _require_project(db, project_id)
    return completion_gate(db, project_id)


@router.put("/projects/{project_id}/profile", response_model=OperationalProfileOut)
def upsert_project_profile(
    project_id: UUID,
    payload: OperationalProfileUpsert,
    db: DbSession,
    actor: Actor,
) -> ProjectOperationalProfile:
    authorize_mutation(db, actor)
    _require_project(db, project_id)
    if payload.operational_status == "completed":
        gate = completion_gate(db, project_id)
        if not gate.accepted:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "completion evidence gate rejected",
                    "gate": gate.model_dump(mode="json"),
                },
            )

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
    authorize_mutation(
        db,
        actor,
        permission=AgentPermission.recompute_project_health,
    )
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
    authorize_mutation(
        db,
        actor,
        permission=AgentPermission.manage_collectors,
    )
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


@router.post(
    "/projects/{project_id}/collectors/{collector_key}/executions",
    response_model=CollectorExecutionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_collector_execution(
    project_id: UUID,
    collector_key: str,
    payload: CollectorExecutionCreate,
    db: DbSession,
    actor: Actor,
) -> CollectorExecution:
    authorize_mutation(
        db,
        actor,
        permission=AgentPermission.record_collector_execution,
    )
    _require_project(db, project_id)
    collector = db.scalar(
        select(CollectorRegistration).where(
            CollectorRegistration.project_id == project_id,
            CollectorRegistration.key == collector_key,
        )
    )
    if collector is None:
        raise HTTPException(status_code=404, detail="collector not found")

    execution = CollectorExecution(collector_id=collector.id, **payload.model_dump())
    db.add(execution)

    if payload.status == "success":
        collector.status = "healthy"
        collector.last_success_at = payload.finished_at
        collector.consecutive_failures = 0
    elif payload.status == "degraded":
        collector.status = "degraded"
        collector.last_success_at = payload.finished_at
    elif payload.status == "failure":
        collector.consecutive_failures += 1
        collector.last_failure_at = payload.finished_at
        collector.status = "failing" if collector.consecutive_failures >= 3 else "degraded"
    if payload.latency_ms is not None:
        collector.last_latency_ms = payload.latency_ms

    db.flush()
    record_audit(
        db,
        actor=actor,
        action="collector.execution_recorded",
        entity_type="collector_execution",
        entity_id=str(execution.id),
        payload={
            "project_id": str(project_id),
            "collector_key": collector_key,
            "status": payload.status,
        },
    )
    db.commit()
    db.refresh(execution)
    return execution


@router.get(
    "/projects/{project_id}/collectors/{collector_key}/executions",
    response_model=list[CollectorExecutionOut],
)
def list_collector_executions(
    project_id: UUID,
    collector_key: str,
    db: DbSession,
) -> list[CollectorExecution]:
    _require_project(db, project_id)
    collector = db.scalar(
        select(CollectorRegistration).where(
            CollectorRegistration.project_id == project_id,
            CollectorRegistration.key == collector_key,
        )
    )
    if collector is None:
        raise HTTPException(status_code=404, detail="collector not found")
    return list(
        db.scalars(
            select(CollectorExecution)
            .where(CollectorExecution.collector_id == collector.id)
            .order_by(CollectorExecution.started_at.desc())
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


@router.get(\n    "/risks",\n    response_model=list[RiskOut],\n    dependencies=[Depends(require_governance_read)],\n)
def list_risks(db: DbSession, project_id: UUID | None = None) -> list[RiskRegisterEntry]:
    statement = select(RiskRegisterEntry).order_by(
        RiskRegisterEntry.severity.desc(), RiskRegisterEntry.date_detected.desc()
    )
    if project_id is not None:
        statement = statement.where(RiskRegisterEntry.project_id == project_id)
    return list(db.scalars(statement))


@router.post("/security/findings", response_model=SecurityFindingOut, status_code=201)
def create_security_finding(
    payload: SecurityFindingCreate,
    db: DbSession,
    actor: Actor,
) -> SecurityFinding:
    authorize_mutation(db, actor)
    if payload.project_id is not None:
        _require_project(db, payload.project_id)
    values = payload.model_dump(exclude_none=True)
    finding = SecurityFinding(**values)
    db.add(finding)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="security_finding.created",
        entity_type="security_finding",
        entity_id=str(finding.id),
        payload={"severity": finding.severity, "category": finding.category},
    )
    db.commit()
    db.refresh(finding)
    return finding


@router.get(\n    "/security/findings",\n    response_model=list[SecurityFindingOut],\n    dependencies=[Depends(require_security_read)],\n)
def list_security_findings(
    db: DbSession,
    project_id: UUID | None = None,
) -> list[SecurityFinding]:
    statement = select(SecurityFinding).order_by(
        SecurityFinding.severity.desc(), SecurityFinding.detected_at.desc()
    )
    if project_id is not None:
        statement = statement.where(SecurityFinding.project_id == project_id)
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


@router.get(\n    "/costs/summary",\n    response_model=CostSummary,\n    dependencies=[Depends(require_financial_read)],\n)
def get_cost_summary(db: DbSession, project_id: UUID | None = None) -> CostSummary:
    if project_id is not None:
        _require_project(db, project_id)
    return summarize_costs(db, project_id)


@router.post("/projects/{project_id}/finops/analyze", response_model=FinOpsAnalysisOut)
def analyze_project_finops(
    project_id: UUID,
    db: DbSession,
    actor: Actor,
) -> FinOpsAnalysisOut:
    authorize_mutation(db, actor)
    _require_project(db, project_id)
    result = analyze_finops(db, project_id)
    record_audit(
        db,
        actor=actor,
        action="finops.analyzed",
        entity_type="project",
        entity_id=str(project_id),
        payload={"anomaly_count": len(result.anomalies)},
    )
    db.commit()
    return result


@router.post("/revenues", response_model=RevenueOut, status_code=status.HTTP_201_CREATED)
def create_revenue(payload: RevenueCreate, db: DbSession, actor: Actor) -> RevenueEntry:
    authorize_mutation(db, actor)
    if payload.project_id is not None:
        _require_project(db, payload.project_id)
    revenue = RevenueEntry(**payload.model_dump())
    db.add(revenue)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="revenue.recorded",
        entity_type="revenue_entry",
        entity_id=str(revenue.id),
        payload={"source": revenue.source, "currency": revenue.currency},
    )
    db.commit()
    db.refresh(revenue)
    return revenue


@router.get(\n    "/revenues/summary",\n    response_model=RevenueSummary,\n    dependencies=[Depends(require_financial_read)],\n)
def get_revenue_summary(db: DbSession, project_id: UUID | None = None) -> RevenueSummary:
    if project_id is not None:
        _require_project(db, project_id)
    return summarize_revenues(db, project_id)


@router.post(
    "/financial-snapshots",
    response_model=FinancialSnapshotOut,
    status_code=status.HTTP_201_CREATED,
)
def create_financial_snapshot(
    payload: FinancialSnapshotCreate,
    db: DbSession,
    actor: Actor,
) -> FinancialSnapshot:
    authorize_mutation(db, actor)
    _require_project(db, payload.project_id)
    snapshot = FinancialSnapshot(**payload.model_dump())
    db.add(snapshot)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="financial_snapshot.created",
        entity_type="financial_snapshot",
        entity_id=str(snapshot.id),
        payload={
            "project_id": str(snapshot.project_id),
            "currency": snapshot.currency,
            "confidence": snapshot.confidence,
        },
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get(\n    "/financial-snapshots",\n    response_model=list[FinancialSnapshotOut],\n    dependencies=[Depends(require_financial_read)],\n)
def list_financial_snapshots(
    db: DbSession,
    project_id: UUID | None = None,
) -> list[FinancialSnapshot]:
    statement = select(FinancialSnapshot).order_by(FinancialSnapshot.computed_at.desc())
    if project_id is not None:
        statement = statement.where(FinancialSnapshot.project_id == project_id)
    return list(db.scalars(statement))


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


@router.post("/ventures/{venture_key}/evaluate", response_model=VentureGateOut)
def evaluate_venture_gate(
    venture_key: str,
    db: DbSession,
    actor: Actor,
) -> VentureGateOut:
    authorize_mutation(db, actor)
    venture = db.scalar(select(VentureEvaluation).where(VentureEvaluation.key == venture_key))
    if venture is None:
        raise HTTPException(status_code=404, detail="venture not found")
    result = evaluate_venture(venture)
    record_audit(
        db,
        actor=actor,
        action="venture.gate_evaluated",
        entity_type="venture_evaluation",
        entity_id=str(venture.id),
        payload={"key": venture.key, "decision": result.decision, "reasons": result.reasons},
    )
    db.commit()
    return result


@router.get("/ventures", response_model=list[VentureOut])
def list_ventures(db: DbSession) -> list[VentureEvaluation]:
    return list(db.scalars(select(VentureEvaluation).order_by(VentureEvaluation.created_at.desc())))


@router.post(
    "/resource-allocations",
    response_model=ResourceAllocationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_resource_allocation(
    payload: ResourceAllocationCreate,
    db: DbSession,
    actor: Actor,
) -> ResourceAllocationEntry:
    authorize_mutation(db, actor)
    if payload.project_id is not None:
        _require_project(db, payload.project_id)
    if payload.resource_type == "budget" and payload.status in {"approved", "active"}:
        _require_human(actor, "budget allocation approval requires a human owner")
    allocation = ResourceAllocationEntry(**payload.model_dump())
    db.add(allocation)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="resource_allocation.created",
        entity_type="resource_allocation",
        entity_id=str(allocation.id),
        payload={
            "resource_type": allocation.resource_type,
            "status": allocation.status,
            "allocated_units": allocation.allocated_units,
        },
    )
    db.commit()
    db.refresh(allocation)
    return allocation


@router.get(\n    "/resource-allocations",\n    response_model=list[ResourceAllocationOut],\n    dependencies=[Depends(require_financial_read)],\n)
def list_resource_allocations(
    db: DbSession,
    project_id: UUID | None = None,
) -> list[ResourceAllocationEntry]:
    statement = select(ResourceAllocationEntry).order_by(ResourceAllocationEntry.created_at.desc())
    if project_id is not None:
        statement = statement.where(ResourceAllocationEntry.project_id == project_id)
    return list(db.scalars(statement))


@router.post(
    "/portfolio-reviews",
    response_model=PortfolioReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_portfolio_review(
    payload: PortfolioReviewCreate,
    db: DbSession,
    actor: Actor,
) -> PortfolioReview:
    authorize_mutation(db, actor)
    _require_project(db, payload.project_id)
    if payload.classification == "sunset":
        _require_human(actor, "sunset recommendation requires a human owner")
    review = PortfolioReview(**payload.model_dump())
    db.add(review)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="portfolio_review.created",
        entity_type="portfolio_review",
        entity_id=str(review.id),
        payload={
            "project_id": str(review.project_id),
            "classification": review.classification,
        },
    )
    db.commit()
    db.refresh(review)
    return review


@router.get(\n    "/portfolio-reviews",\n    response_model=list[PortfolioReviewOut],\n    dependencies=[Depends(require_governance_read)],\n)
def list_portfolio_reviews(
    db: DbSession,
    project_id: UUID | None = None,
) -> list[PortfolioReview]:
    statement = select(PortfolioReview).order_by(PortfolioReview.reviewed_at.desc())
    if project_id is not None:
        statement = statement.where(PortfolioReview.project_id == project_id)
    return list(db.scalars(statement))


@router.post(
    "/tool-decisions",
    response_model=ToolDecisionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_tool_decision(
    payload: ToolDecisionCreate,
    db: DbSession,
    actor: Actor,
) -> ToolDecision:
    authorize_mutation(db, actor)
    decision = ToolDecision(**payload.model_dump())
    db.add(decision)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="tool decision already exists") from exc
    record_audit(
        db,
        actor=actor,
        action="tool_decision.created",
        entity_type="tool_decision",
        entity_id=str(decision.id),
        payload={
            "key": decision.key,
            "tool_name": decision.tool_name,
            "classification": decision.classification,
        },
    )
    db.commit()
    db.refresh(decision)
    return decision


@router.get(\n    "/tool-decisions",\n    response_model=list[ToolDecisionOut],\n    dependencies=[Depends(require_governance_read)],\n)
def list_tool_decisions(db: DbSession) -> list[ToolDecision]:
    return list(db.scalars(select(ToolDecision).order_by(ToolDecision.reviewed_at.desc())))


@router.get("/executive-state", response_model=ExecutiveStateOut)
def get_executive_state(db: DbSession) -> ExecutiveStateOut:
    return executive_state(db)
