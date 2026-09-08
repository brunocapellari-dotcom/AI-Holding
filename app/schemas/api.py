from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import (
    CriterionStatus,
    DecisionStatus,
    ProjectStatus,
    RiskLevel,
    WorkStatus,
)

KEY_PATTERN = r"^[A-Z0-9][A-Z0-9_-]*$"


class ExecutionKind(StrEnum):
    control_plane_health = "control_plane_health"


class ProjectCreate(BaseModel):
    key: str = Field(min_length=2, max_length=40, pattern=KEY_PATTERN)
    name: str = Field(min_length=2, max_length=200)
    priority: int = Field(default=3, ge=0, le=5)
    autonomy_level: int = Field(default=3, ge=0, le=6)
    parent_project_id: UUID | None = None
    owner_agent_id: UUID | None = None
    repository: str | None = Field(default=None, max_length=240)
    repository_path: str | None = Field(default=None, max_length=240)
    business_unit: str | None = Field(default=None, max_length=120)
    strategic_goal: str = Field(min_length=5)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class ProjectOut(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: ProjectStatus
    version: int
    created_at: datetime
    updated_at: datetime


class MilestoneCreate(BaseModel):
    key: str = Field(min_length=2, max_length=60, pattern=KEY_PATTERN)
    title: str = Field(min_length=3, max_length=220)
    objective: str = Field(min_length=5)
    weight: int = Field(default=1, ge=1, le=100)
    target_date: date | None = None


class MilestoneOut(MilestoneCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    status: WorkStatus


class CriterionCreate(BaseModel):
    key: str = Field(min_length=2, max_length=60, pattern=KEY_PATTERN)
    description: str = Field(min_length=5)
    weight: int = Field(default=1, ge=1, le=100)


class CriterionOut(CriterionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    milestone_id: UUID
    status: CriterionStatus
    verifier: str | None
    evidence: list[object]
    verified_at: datetime | None


class CriterionVerify(BaseModel):
    evidence: list[dict[str, object] | str] = Field(min_length=1)


class TaskCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=KEY_PATTERN)
    project_id: UUID
    milestone_id: UUID | None = None
    title: str = Field(min_length=3, max_length=240)
    description: str = ""
    priority: int = Field(default=3, ge=0, le=5)
    assigned_agent_id: UUID | None = None
    execution_kind: ExecutionKind | None = None
    depends_on: list[UUID] = Field(default_factory=list)
    due_at: datetime | None = None
    idempotency_key: str = Field(min_length=8, max_length=160)
    metadata_json: dict[str, object] = Field(default_factory=dict)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    project_id: UUID
    milestone_id: UUID | None
    title: str
    description: str
    priority: int
    assigned_agent_id: UUID | None
    execution_kind: ExecutionKind | None
    due_at: datetime | None
    status: WorkStatus
    blocked_reason: str | None
    idempotency_key: str
    metadata_json: dict[str, object]


class TaskTransition(BaseModel):
    status: WorkStatus
    blocked_reason: str | None = None


class DecisionCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=KEY_PATTERN)
    project_id: UUID
    title: str = Field(min_length=3, max_length=240)
    context: str = Field(min_length=5)
    recommendation: str | None = None
    risk_level: RiskLevel = RiskLevel.medium
    requires_human: bool = True
    options: list[dict[str, object] | str] = Field(default_factory=list)
    due_at: datetime | None = None


class DecisionOut(DecisionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: DecisionStatus
    resolution: dict[str, object]


class DecisionResolve(BaseModel):
    outcome: DecisionStatus
    rationale: str | None = None


class ProjectProgress(BaseModel):
    project_id: UUID
    progress_pct: float
    milestones_total: int
    criteria_total: int
    criteria_verified: int


class ExecutiveSummary(BaseModel):
    active_projects: int
    running_tasks: int
    blocked_tasks: int
    pending_human_decisions: int
    open_incidents: int
    portfolio_progress_pct: float
