from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectStatus(StrEnum):
    active = "active"
    paused = "paused"
    incubating = "incubating"
    archived = "archived"


class WorkStatus(StrEnum):
    planned = "planned"
    ready = "ready"
    running = "running"
    blocked = "blocked"
    review = "review"
    done = "done"
    cancelled = "cancelled"


class CriterionStatus(StrEnum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"


class DecisionStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    superseded = "superseded"


class IncidentStatus(StrEnum):
    open = "open"
    investigating = "investigating"
    mitigated = "mitigated"
    resolved = "resolved"


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class AgentStatus(StrEnum):
    active = "active"
    disabled = "disabled"
    degraded = "degraded"


class RiskLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Severity(StrEnum):
    sev1 = "sev1"
    sev2 = "sev2"
    sev3 = "sev3"
    sev4 = "sev4"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = (CheckConstraint("max_autonomy BETWEEN 0 AND 6", name="autonomy_range"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    role: Mapped[str] = mapped_column(String(160))
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.active)
    max_autonomy: Mapped[int] = mapped_column(Integer, default=3)
    model_policy: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    capabilities: Mapped[list[object]] = mapped_column(JSON, default=list)


class Project(Base, TimestampMixin):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("priority BETWEEN 0 AND 5", name="priority_range"),
        CheckConstraint("autonomy_level BETWEEN 0 AND 6", name="autonomy_range"),
        CheckConstraint(
            "parent_project_id IS NULL OR parent_project_id <> id",
            name="no_self_parent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.active)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    autonomy_level: Mapped[int] = mapped_column(Integer, default=3)
    parent_project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    repository: Mapped[str | None] = mapped_column(String(240), nullable=True)
    repository_path: Mapped[str | None] = mapped_column(String(240), nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(120), nullable=True)
    strategic_goal: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    milestones: Mapped[list[Milestone]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"version_id_col": version}


class Milestone(Base, TimestampMixin):
    __tablename__ = "milestones"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_milestone_project_key"),
        CheckConstraint("weight BETWEEN 1 AND 100", name="weight_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(220))
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[WorkStatus] = mapped_column(Enum(WorkStatus), default=WorkStatus.planned)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    project: Mapped[Project] = relationship(back_populates="milestones")
    criteria: Mapped[list[AcceptanceCriterion]] = relationship(
        back_populates="milestone", cascade="all, delete-orphan"
    )


class AcceptanceCriterion(Base, TimestampMixin):
    __tablename__ = "acceptance_criteria"
    __table_args__ = (
        UniqueConstraint("milestone_id", "key", name="uq_criterion_milestone_key"),
        CheckConstraint("weight BETWEEN 1 AND 100", name="weight_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    milestone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("milestones.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(60))
    description: Mapped[str] = mapped_column(Text)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[CriterionStatus] = mapped_column(
        Enum(CriterionStatus), default=CriterionStatus.pending
    )
    verifier: Mapped[str | None] = mapped_column(String(160), nullable=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    milestone: Mapped[Milestone] = relationship(back_populates="criteria")


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_task_project_key"),
        UniqueConstraint("idempotency_key", name="uq_task_idempotency_key"),
        CheckConstraint("priority BETWEEN 0 AND 5", name="priority_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(80))
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    milestone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[WorkStatus] = mapped_column(Enum(WorkStatus), default=WorkStatus.planned)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    depends_on_task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )


class Run(Base, TimestampMixin):
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("external_run_id", name="uq_run_external_run_id"),
        CheckConstraint("attempt >= 1", name="attempt_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.queued)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    external_run_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    output_metadata: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Decision(Base, TimestampMixin):
    __tablename__ = "decisions"
    __table_args__ = (UniqueConstraint("project_id", "key", name="uq_decision_project_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(80))
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    context: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.medium)
    status: Mapped[DecisionStatus] = mapped_column(
        Enum(DecisionStatus), default=DecisionStatus.pending
    )
    requires_human: Mapped[bool] = mapped_column(Boolean, default=True)
    options: Mapped[list[object]] = mapped_column(JSON, default=list)
    resolution: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"), index=True
    )
    actor: Mapped[str] = mapped_column(String(160), index=True)
    outcome: Mapped[DecisionStatus] = mapped_column(Enum(DecisionStatus))
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    severity: Mapped[Severity] = mapped_column(Enum(Severity), index=True)
    title: Mapped[str] = mapped_column(String(240))
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus), default=IncidentStatus.open
    )
    source: Mapped[str] = mapped_column(String(120))
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(160), index=True)
    actor_type: Mapped[str] = mapped_column(String(40), default="agent")
    action: Mapped[str] = mapped_column(String(160), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
