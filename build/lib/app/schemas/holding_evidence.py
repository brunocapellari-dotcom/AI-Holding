from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CollectorExecutionCreate(BaseModel):
    status: Literal["running", "success", "degraded", "failure"]
    started_at: datetime
    finished_at: datetime | None = None
    source_cursor: str | None = Field(default=None, max_length=500)
    latency_ms: int | None = Field(default=None, ge=0)
    records_seen: int = Field(default=0, ge=0)
    records_written: int = Field(default=0, ge=0)
    error_class: str | None = Field(default=None, max_length=160)
    error_message: str | None = None
    evidence: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_execution(self) -> CollectorExecutionCreate:
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at must be on or after started_at")
        if self.status == "running" and self.finished_at is not None:
            raise ValueError("running execution cannot have finished_at")
        if self.status != "running" and self.finished_at is None:
            raise ValueError("finished execution requires finished_at")
        if self.records_written > self.records_seen:
            raise ValueError("records_written cannot exceed records_seen")
        if self.status == "failure" and not (self.error_class or self.error_message):
            raise ValueError("failure execution requires error details")
        return self


class CollectorExecutionOut(CollectorExecutionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    collector_id: UUID


class SecurityFindingCreate(BaseModel):
    project_id: UUID | None = None
    source: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=120)
    severity: Literal["info", "low", "medium", "high", "critical"]
    status: Literal["open", "mitigating", "accepted", "resolved", "false_positive"] = "open"
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3)
    remediation: str = ""
    evidence: list[object] = Field(default_factory=list)
    detected_at: datetime | None = None
    resolved_at: datetime | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_resolution(self) -> SecurityFindingCreate:
        if self.status in {"resolved", "false_positive"} and self.resolved_at is None:
            raise ValueError("resolved findings require resolved_at")
        if self.status not in {"resolved", "false_positive"} and self.resolved_at is not None:
            raise ValueError("open findings cannot have resolved_at")
        if self.detected_at and self.resolved_at and self.resolved_at < self.detected_at:
            raise ValueError("resolved_at must be on or after detected_at")
        return self


class SecurityFindingOut(SecurityFindingCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    detected_at: datetime
    created_at: datetime
    updated_at: datetime


class ExecutionFabricProjectState(BaseModel):
    project_id: UUID
    project_key: str
    name: str
    repository: str | None = None
    health_state: str
    health_score: int = Field(ge=0, le=100)
    cloud_build_state: str
    build_id: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    log_url: str | None = None
    evidence_uri: str | None = None
    failure_type: str | None = None
    failed_step_id: str | None = None
    failed_step_name: str | None = None
    failed_step_exit_code: int | None = None
    failure_category: str | None = None
    remediation_owner: str | None = None
    recommended_action: str | None = None
    retry_safe: bool = False
    observed_at: datetime | None = None


class ExecutionFabricOut(BaseModel):
    generated_at: datetime
    totals: dict[str, int]
    projects: list[ExecutionFabricProjectState]
