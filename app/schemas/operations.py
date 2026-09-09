from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.entities import AgentStatus, IncidentStatus, RunStatus, Severity
from app.schemas.api import KEY_PATTERN, ExecutionKind, TaskOut


class AgentCreate(BaseModel):
    key: str = Field(min_length=2, max_length=80, pattern=KEY_PATTERN)
    name: str = Field(min_length=2, max_length=160)
    role: str = Field(min_length=2, max_length=160)
    max_autonomy: int = Field(default=3, ge=0, le=6)
    model_policy: dict[str, object] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list, max_length=100)


class AgentOut(AgentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: AgentStatus
    created_at: datetime
    updated_at: datetime


class AgentTransition(BaseModel):
    status: AgentStatus


class RunCreate(BaseModel):
    task_id: UUID
    agent_id: UUID | None = None
    external_run_id: str | None = Field(default=None, min_length=3, max_length=200)
    input_metadata: dict[str, object] = Field(default_factory=dict)


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    agent_id: UUID | None
    status: RunStatus
    attempt: int
    external_run_id: str | None
    input_metadata: dict[str, object]
    output_metadata: dict[str, object]
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RunTransition(BaseModel):
    status: RunStatus
    output_metadata: dict[str, object] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=10000)

    @model_validator(mode="after")
    def validate_terminal_payload(self) -> "RunTransition":
        if self.status == RunStatus.failed and not self.error:
            raise ValueError("error is required for failed runs")
        if self.status != RunStatus.failed and self.error:
            raise ValueError("error is only valid for failed runs")
        return self


class TaskClaimRequest(BaseModel):
    agent_id: UUID
    project_id: UUID | None = None
    execution_kinds: list[ExecutionKind] = Field(min_length=1, max_length=10)


class TaskClaimOut(BaseModel):
    task: TaskOut
    run: RunOut


class IncidentCreate(BaseModel):
    project_id: UUID | None = None
    severity: Severity
    title: str = Field(min_length=3, max_length=240)
    source: str = Field(min_length=2, max_length=120)
    details: dict[str, object] = Field(default_factory=dict)


class IncidentOut(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: IncidentStatus
    root_cause: str | None
    resolution: dict[str, object]
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IncidentTransition(BaseModel):
    status: IncidentStatus
    root_cause: str | None = Field(default=None, max_length=10000)
    resolution: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_resolution(self) -> "IncidentTransition":
        if self.status == IncidentStatus.resolved and not self.resolution:
            raise ValueError("resolution evidence is required when resolving an incident")
        return self
