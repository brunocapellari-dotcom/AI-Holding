from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

OperationalStatus = Literal[
    "planned",
    "ready",
    "running",
    "completed",
    "failed",
    "blocked",
    "paused",
    "cancelled",
]
HealthState = Literal["healthy", "degraded", "at_risk", "blocked", "offline"]
SecurityLevel = Literal["public", "internal", "confidential", "restricted"]
AlertLevel = Literal["info", "watch", "action_required", "critical"]
DependencyType = Literal[
    "project",
    "service",
    "data",
    "api",
    "agent",
    "skill",
    "model",
    "infrastructure",
]


class OperationalProfileUpsert(BaseModel):
    mission: str = ""
    operational_status: OperationalStatus = "planned"
    knowledge_namespace: str | None = None
    current_phase: str | None = None
    security_level: SecurityLevel = "internal"
    budget_micros: int = Field(default=0, ge=0)
    budget_currency: str = Field(default="BRL", min_length=3, max_length=3)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class OperationalProfileOut(OperationalProfileUpsert):
    model_config = ConfigDict(from_attributes=True)
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class CollectorUpsert(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    source: str = Field(min_length=2, max_length=240)
    data_type: str = Field(min_length=2, max_length=120)
    frequency_seconds: int = Field(gt=0)
    freshness_sla_seconds: int = Field(gt=0)
    retry_policy: dict[str, object] = Field(default_factory=dict)
    status: Literal["healthy", "degraded", "failing", "disabled"] = "degraded"
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_latency_ms: int | None = Field(default=None, ge=0)
    consecutive_failures: int = Field(default=0, ge=0)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CollectorOut(CollectorUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    created_at: datetime
    updated_at: datetime


class RiskCreate(BaseModel):
    project_id: UUID | None = None
    key: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=3)
    probability: int = Field(ge=0, le=100)
    impact: int = Field(ge=1, le=5)
    severity: Literal["low", "medium", "high", "critical"]
    mitigation: str = ""
    owner: str = Field(default="risk-ai", min_length=2, max_length=160)
    status: Literal["open", "mitigating", "accepted", "resolved"] = "open"
    last_review: datetime | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RiskOut(RiskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    date_detected: datetime
    created_at: datetime
    updated_at: datetime


class CostCreate(BaseModel):
    project_id: UUID | None = None
    provider: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    amount_micros: int = Field(ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    units: dict[str, object] = Field(default_factory=dict)
    observed_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class CostOut(CostCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class RevenueCreate(BaseModel):
    project_id: UUID | None = None
    source: str = Field(min_length=2, max_length=160)
    amount_micros: int = Field(ge=0)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    observed_at: datetime
    metadata_json: dict[str, object] = Field(default_factory=dict)


class RevenueOut(RevenueCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class FinancialSnapshotCreate(BaseModel):
    project_id: UUID
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    period_start: datetime
    period_end: datetime
    revenue_micros: int = Field(default=0, ge=0)
    cost_micros: int = Field(default=0, ge=0)
    budget_micros: int = Field(default=0, ge=0)
    runway_days: int | None = Field(default=None, ge=0)
    payback_days: int | None = Field(default=None, ge=0)
    roi_estimate_bps: int | None = None
    confidence: int = Field(default=0, ge=0, le=100)
    assumptions: list[object] = Field(default_factory=list)

    @model_validator(mode="after")
    def period_is_ordered(self) -> FinancialSnapshotCreate:
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class FinancialSnapshotOut(FinancialSnapshotCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    computed_at: datetime


class DependencyCreate(BaseModel):
    source_type: DependencyType
    source_key: str = Field(min_length=1, max_length=200)
    target_type: DependencyType
    target_key: str = Field(min_length=1, max_length=200)
    criticality: int = Field(default=3, ge=1, le=5)
    blocking: bool = True
    status: Literal["healthy", "degraded", "blocked", "offline"] = "healthy"
    metadata_json: dict[str, object] = Field(default_factory=dict)


class DependencyOut(DependencyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class AlertCreate(BaseModel):
    project_id: UUID | None = None
    level: AlertLevel
    source: str = Field(min_length=2, max_length=120)
    dedupe_key: str = Field(min_length=2, max_length=220)
    title: str = Field(min_length=3, max_length=240)
    details: dict[str, object] = Field(default_factory=dict)
    status: Literal["active", "resolved"] = "active"


class AlertOut(AlertCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    occurrences: int
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class IntegrationUpsert(BaseModel):
    service_key: str = Field(min_length=2, max_length=100)
    kind: str = Field(min_length=2, max_length=80)
    status: Literal["healthy", "degraded", "blocked", "offline", "unconfigured"] = "unconfigured"
    endpoint: str | None = Field(default=None, max_length=500)
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    freshness_sla_seconds: int | None = Field(default=None, gt=0)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class IntegrationOut(IntegrationUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class VentureCreate(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=220)
    stage: str = Field(default="idea", min_length=2, max_length=80)
    automation_pct: int = Field(default=0, ge=0, le=100)
    unit_economics: dict[str, object] = Field(default_factory=dict)
    risk_summary: dict[str, object] = Field(default_factory=dict)
    validation_cost_micros: int = Field(default=0, ge=0)
    decision: Literal["research", "build", "hold", "reject"] = "research"
    evidence: list[object] = Field(default_factory=list)


class VentureOut(VentureCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class ResourceAllocationCreate(BaseModel):
    project_id: UUID | None = None
    resource_type: Literal["cpu", "gpu", "storage", "agent", "model", "budget", "developer"]
    resource_key: str = Field(min_length=1, max_length=160)
    requested_units: int = Field(default=0, ge=0)
    allocated_units: int = Field(default=0, ge=0)
    unit: str = Field(min_length=1, max_length=40)
    status: Literal["proposed", "approved", "active", "reduced", "released", "rejected"] = (
        "proposed"
    )
    reason: str = ""
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def dates_are_ordered(self) -> ResourceAllocationCreate:
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("ends_at must be on or after starts_at")
        return self


class ResourceAllocationOut(ResourceAllocationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class PortfolioReviewCreate(BaseModel):
    project_id: UUID
    classification: Literal["accelerate", "maintain", "restructure", "pause", "sunset"]
    value_score: int = Field(ge=0, le=100)
    progress_score: int = Field(ge=0, le=100)
    cost_score: int = Field(ge=0, le=100)
    complexity_score: int = Field(ge=0, le=100)
    risk_score: int = Field(ge=0, le=100)
    monetization_score: int = Field(ge=0, le=100)
    dependency_score: int = Field(ge=0, le=100)
    requires_owner_approval: bool = False
    rationale: str = Field(min_length=3)
    evidence: list[object] = Field(default_factory=list)

    @model_validator(mode="after")
    def irreversible_recommendations_need_owner(self) -> PortfolioReviewCreate:
        if self.classification == "sunset" and not self.requires_owner_approval:
            raise ValueError("sunset recommendation requires owner approval")
        return self


class PortfolioReviewOut(PortfolioReviewCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reviewed_at: datetime
    created_at: datetime
    updated_at: datetime


class ToolDecisionCreate(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    tool_name: str = Field(min_length=2, max_length=160)
    capability: str = Field(min_length=2, max_length=160)
    classification: Literal["adopt", "replace", "benchmark", "reserve", "reject"]
    replaces_key: str | None = Field(default=None, max_length=120)
    benefit: str = ""
    maintenance_cost: str = ""
    license: str = Field(default="unknown", max_length=120)
    risk: str = ""
    rationale: str = Field(min_length=3)
    evidence: list[object] = Field(default_factory=list)

    @model_validator(mode="after")
    def replacement_names_existing_decision(self) -> ToolDecisionCreate:
        if self.classification == "replace" and not self.replaces_key:
            raise ValueError("replace classification requires replaces_key")
        return self


class ToolDecisionOut(ToolDecisionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    reviewed_at: datetime
    created_at: datetime
    updated_at: datetime


class HealthOut(BaseModel):
    project_id: UUID
    state: HealthState
    score: int = Field(ge=0, le=100)
    dimensions: dict[str, object]
    reasons: list[object]
    computed_at: datetime


class CostSummary(BaseModel):
    project_id: UUID | None
    totals_by_currency: dict[str, int]
    by_category: dict[str, dict[str, int]]
    by_provider: dict[str, dict[str, int]]


class RevenueSummary(BaseModel):
    project_id: UUID | None
    totals_by_currency: dict[str, int]
    by_source: dict[str, dict[str, int]]


class ProjectContractOut(BaseModel):
    project_id: UUID
    project_key: str
    name: str
    status: OperationalStatus
    capabilities: list[object]
    tasks: list[dict[str, object]]
    blockers: list[dict[str, object]]
    cost: CostSummary
    revenue: RevenueSummary
    security: dict[str, object]
    data_health: dict[str, object]
    health: HealthOut
    alerts: list[AlertOut]


class ProjectRegistryEntryOut(BaseModel):
    project_id: UUID
    project_key: str
    name: str
    repository: str | None
    legacy_status: str
    operational_status: OperationalStatus
    priority: int
    autonomy_level: int
    business_unit: str | None
    mission: str
    current_phase: str | None
    knowledge_namespace: str | None
    security_level: SecurityLevel
    budget_micros: int
    budget_currency: str
    health: HealthOut


class ExecutiveStateOut(BaseModel):
    generated_at: datetime
    running: list[dict[str, object]]
    completed: list[dict[str, object]]
    failed: list[dict[str, object]]
    blocked: list[dict[str, object]]
    owner_actions: list[dict[str, object]]
    costs: dict[str, object]
    revenues: dict[str, object]
    risks: list[dict[str, object]]
    priorities: list[dict[str, object]]
    execution_fabric: dict[str, object] = Field(default_factory=dict)
