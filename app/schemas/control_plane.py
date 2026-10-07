from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


PriorityTier = Literal["P0", "P1", "P2", "P3"]
ReleaseStatus = Literal[
    "PLANNED", "IN_PROGRESS", "BLOCKED", "TESTING", "REVIEW",
    "READY", "RELEASED", "FAILED", "ROLLED_BACK"
]
CommercialStatus = Literal["NOT_READY", "DEMO", "PILOT", "SELLABLE", "CUSTOMERS", "SCALING"]
GateType = Literal["CODE", "TEST", "SECURITY", "E2E", "DEPLOY", "OPERATIONS", "COMMERCIAL"]
GateStatus = Literal["NOT_STARTED", "IN_PROGRESS", "PASS", "FAIL", "WAIVED"]
EvidenceKind = Literal[
    "COMMIT", "PR", "CI_RUN", "TEST_RESULT", "SCREENSHOT", "LOG",
    "ENDPOINT_HEALTH", "DEPLOYMENT", "ARTIFACT", "REPORT", "E2E_EXECUTION"
]
VerificationStatus = Literal["PENDING", "VERIFIED", "REJECTED"]


class GovernanceUpsert(BaseModel):
    declared_status: Literal[
        "ACTIVE", "PAUSED", "BLOCKED", "MAINTENANCE", "ARCHIVED",
        "DISCONTINUED", "DONE", "UNKNOWN"
    ] = "UNKNOWN"
    priority_tier: PriorityTier = "P2"
    current_release_id: UUID | None = None
    commercial_status: CommercialStatus = "NOT_READY"
    monthly_budget_micros: int = Field(default=0, ge=0)
    next_best_action: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)


class GovernanceOut(GovernanceUpsert):
    model_config = ConfigDict(from_attributes=True)
    project_id: UUID
    verified_status: str
    health_status: str
    cost_status: str
    last_activity: datetime | None
    last_verified_activity: datetime | None
    stalled: bool
    execution_risk: bool
    scope_creep: bool
    created_at: datetime
    updated_at: datetime


class ReleaseCreate(BaseModel):
    project_id: UUID
    name: str = Field(min_length=2, max_length=180)
    target_date: date | None = None
    scope: list[dict[str, object] | str] = Field(default_factory=list)
    dependencies: list[dict[str, object] | str] = Field(default_factory=list)
    commercial_status: CommercialStatus = "NOT_READY"
    metadata_json: dict[str, object] = Field(default_factory=dict)


class ReleaseOut(ReleaseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: ReleaseStatus
    evidence_summary: list[object]
    created_at: datetime
    updated_at: datetime


class ReleaseStatusUpdate(BaseModel):
    status: ReleaseStatus
    commercial_status: CommercialStatus | None = None


class GateUpsert(BaseModel):
    gate_type: GateType
    status: GateStatus
    evidence_required: bool = True
    notes: str = ""


class GateOut(GateUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    release_id: UUID
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EvidenceCreate(BaseModel):
    project_id: UUID | None = None
    task_id: UUID | None = None
    release_id: UUID | None = None
    kind: EvidenceKind
    source: str = Field(min_length=1, max_length=160)
    artifact_reference: str = Field(min_length=1)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class EvidenceOut(EvidenceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    verification_status: VerificationStatus
    observed_at: datetime
    verified_at: datetime | None


class EvidenceVerify(BaseModel):
    verification_status: Literal["VERIFIED", "REJECTED"]


class ServiceUpsert(BaseModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=180)
    environment: str = Field(min_length=1, max_length=80)
    version: str | None = Field(default=None, max_length=120)
    endpoint: str | None = Field(default=None, max_length=500)
    status: Literal["HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN"] = "UNKNOWN"
    last_health_check: datetime | None = None
    last_deploy: datetime | None = None
    dependencies: list[dict[str, object] | str] = Field(default_factory=list)
    owner: str = Field(default="project", max_length=160)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class ServiceOut(ServiceUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class DeploymentCreate(BaseModel):
    project_id: UUID
    service_id: UUID | None = None
    release_id: UUID | None = None
    version: str = Field(min_length=1, max_length=120)
    commit_sha: str = Field(min_length=7, max_length=64)
    environment: str = Field(min_length=1, max_length=80)
    deployment_ref: str = Field(min_length=1, max_length=240)
    started_at: datetime
    finished_at: datetime | None = None
    status: Literal["PENDING", "DEPLOYING", "HEALTHY", "FAILED", "ROLLED_BACK"] = "PENDING"
    rollback_target: str | None = Field(default=None, max_length=240)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class DeploymentOut(DeploymentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class TestCreate(BaseModel):
    project_id: UUID
    release_id: UUID | None = None
    task_id: UUID | None = None
    suite: str = Field(min_length=1, max_length=180)
    test_type: Literal["UNIT", "INTEGRATION", "E2E", "SECURITY", "REGRESSION", "SMOKE"]
    commit_sha: str = Field(min_length=7, max_length=64)
    environment: str = Field(min_length=1, max_length=80)
    result: Literal["PASS", "FAIL", "SKIPPED"]
    failures: list[dict[str, object] | str] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class TestOut(TestCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    observed_at: datetime


class BlockerCreate(BaseModel):
    project_id: UUID
    release_id: UUID | None = None
    task_id: UUID | None = None
    blocker_type: Literal[
        "CREDENTIAL", "ACCESS", "PAYMENT", "LEGAL", "TECHNICAL",
        "EXTERNAL_DEPENDENCY", "HUMAN_DECISION"
    ]
    description: str = Field(min_length=3)
    impact: str = Field(min_length=3)
    owner: str = Field(min_length=1, max_length=160)
    action_required: str = Field(min_length=3)
    priority: PriorityTier = "P0"
    metadata_json: dict[str, object] = Field(default_factory=dict)


class BlockerOut(BlockerCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: Literal["OPEN", "RESOLVED"]
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectOwnerState(BaseModel):
    project_id: UUID
    key: str
    name: str
    project_status: str
    declared_status: str
    verified_status: str
    priority_tier: str
    health_status: str
    commercial_status: str
    cost_status: str
    current_release: str | None
    next_best_action: str | None
    open_blockers: int
    wip: int
    stalled: bool
    execution_risk: bool
    scope_creep: bool


class OwnerView(BaseModel):
    projects: list[ProjectOwnerState]
    active_projects: int
    paused_projects: int
    blocked_projects: int
    sellable_products: int
    releases_at_risk: int
    human_actions: int
    unhealthy_services: int
