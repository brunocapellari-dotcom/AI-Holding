from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.entities import TimestampMixin


class ReleaseRecord(Base, TimestampMixin):
    __tablename__ = "release_registry"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_release_project_name"),
        CheckConstraint(
            "status IN ('PLANNED','IN_PROGRESS','BLOCKED','TESTING','REVIEW','READY','RELEASED','FAILED','ROLLED_BACK')",
            name="release_status_valid",
        ),
        CheckConstraint(
            "commercial_status IN ('NOT_READY','DEMO','PILOT','SELLABLE','CUSTOMERS','SCALING')",
            name="release_commercial_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="PLANNED", index=True)
    scope: Mapped[list[object]] = mapped_column(JSON, default=list)
    dependencies: Mapped[list[object]] = mapped_column(JSON, default=list)
    commercial_status: Mapped[str] = mapped_column(String(24), default="NOT_READY", index=True)
    evidence_summary: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ProjectGovernanceState(Base, TimestampMixin):
    __tablename__ = "project_governance_state"
    __table_args__ = (
        CheckConstraint(
            "declared_status IN ('ACTIVE','PAUSED','BLOCKED','MAINTENANCE','ARCHIVED','DISCONTINUED','DONE','UNKNOWN')",
            name="declared_status_valid",
        ),
        CheckConstraint(
            "verified_status IN ('UNKNOWN','NOT_DONE','BLOCKED','READY','RELEASED','FAILED','STALE')",
            name="verified_status_valid",
        ),
        CheckConstraint("priority_tier IN ('P0','P1','P2','P3')", name="priority_tier_valid"),
        CheckConstraint(
            "health_status IN ('HEALTHY','DEGRADED','UNHEALTHY','UNKNOWN')",
            name="governance_health_valid",
        ),
        CheckConstraint(
            "cost_status IN ('NORMAL','WARNING','OVER_BUDGET')",
            name="governance_cost_status_valid",
        ),
        CheckConstraint(
            "commercial_status IN ('NOT_READY','DEMO','PILOT','SELLABLE','CUSTOMERS','SCALING')",
            name="governance_commercial_status_valid",
        ),
        CheckConstraint("monthly_budget_micros >= 0", name="monthly_budget_nonnegative"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    declared_status: Mapped[str] = mapped_column(String(24), default="UNKNOWN")
    verified_status: Mapped[str] = mapped_column(String(24), default="UNKNOWN", index=True)
    priority_tier: Mapped[str] = mapped_column(String(2), default="P2", index=True)
    current_release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_registry.id", ondelete="SET NULL"), nullable=True, index=True
    )
    health_status: Mapped[str] = mapped_column(String(20), default="UNKNOWN", index=True)
    cost_status: Mapped[str] = mapped_column(String(20), default="NORMAL", index=True)
    commercial_status: Mapped[str] = mapped_column(String(24), default="NOT_READY", index=True)
    monthly_budget_micros: Mapped[int] = mapped_column(Integer, default=0)
    next_best_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_activity: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stalled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_risk: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scope_creep: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ReleaseGateRecord(Base, TimestampMixin):
    __tablename__ = "release_gate_registry"
    __table_args__ = (
        UniqueConstraint("release_id", "gate_type", name="uq_release_gate_type"),
        CheckConstraint(
            "gate_type IN ('CODE','TEST','SECURITY','E2E','DEPLOY','OPERATIONS','COMMERCIAL')",
            name="release_gate_type_valid",
        ),
        CheckConstraint(
            "status IN ('NOT_STARTED','IN_PROGRESS','PASS','FAIL','WAIVED')",
            name="release_gate_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    release_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("release_registry.id", ondelete="CASCADE"), index=True
    )
    gate_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="NOT_STARTED", index=True)
    evidence_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class EvidenceRecord(Base):
    __tablename__ = "evidence_registry"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('COMMIT','PR','CI_RUN','TEST_RESULT','SCREENSHOT','LOG','ENDPOINT_HEALTH','DEPLOYMENT','ARTIFACT','REPORT','E2E_EXECUTION')",
            name="evidence_kind_valid",
        ),
        CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')",
            name="evidence_verification_status_valid",
        ),
        CheckConstraint(
            "task_id IS NOT NULL OR release_id IS NOT NULL OR project_id IS NOT NULL",
            name="evidence_has_owner",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_registry.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(28), index=True)
    source: Mapped[str] = mapped_column(String(160))
    artifact_reference: Mapped[str] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ServiceRecord(Base, TimestampMixin):
    __tablename__ = "service_registry"
    __table_args__ = (
        UniqueConstraint("project_id", "name", "environment", name="uq_service_project_env"),
        CheckConstraint(
            "status IN ('HEALTHY','DEGRADED','UNHEALTHY','UNKNOWN')",
            name="service_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(180))
    environment: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="UNKNOWN", index=True)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_deploy: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dependencies: Mapped[list[object]] = mapped_column(JSON, default=list)
    owner: Mapped[str] = mapped_column(String(160), default="project")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class DeploymentRecord(Base):
    __tablename__ = "deployment_registry"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','DEPLOYING','HEALTHY','FAILED','ROLLED_BACK')",
            name="deployment_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_registry.id", ondelete="SET NULL"), nullable=True, index=True
    )
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_registry.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version: Mapped[str] = mapped_column(String(120))
    commit_sha: Mapped[str] = mapped_column(String(64), index=True)
    environment: Mapped[str] = mapped_column(String(80), index=True)
    deployment_ref: Mapped[str] = mapped_column(String(240), unique=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    rollback_target: Mapped[str | None] = mapped_column(String(240), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class TestRecord(Base):
    __tablename__ = "test_registry"
    __table_args__ = (
        CheckConstraint(
            "test_type IN ('UNIT','INTEGRATION','E2E','SECURITY','REGRESSION','SMOKE')",
            name="test_type_valid",
        ),
        CheckConstraint("result IN ('PASS','FAIL','SKIPPED')", name="test_result_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_registry.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    suite: Mapped[str] = mapped_column(String(180))
    test_type: Mapped[str] = mapped_column(String(20), index=True)
    commit_sha: Mapped[str] = mapped_column(String(64), index=True)
    environment: Mapped[str] = mapped_column(String(80), index=True)
    result: Mapped[str] = mapped_column(String(12), index=True)
    failures: Mapped[list[object]] = mapped_column(JSON, default=list)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class BlockerRecord(Base, TimestampMixin):
    __tablename__ = "blocker_registry"
    __table_args__ = (
        CheckConstraint(
            "blocker_type IN ('CREDENTIAL','ACCESS','PAYMENT','LEGAL','TECHNICAL','EXTERNAL_DEPENDENCY','HUMAN_DECISION')",
            name="blocker_type_valid",
        ),
        CheckConstraint("status IN ('OPEN','RESOLVED')", name="blocker_status_valid"),
        CheckConstraint("priority IN ('P0','P1','P2','P3')", name="blocker_priority_valid"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_registry.id", ondelete="CASCADE"), nullable=True, index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    blocker_type: Mapped[str] = mapped_column(String(28), index=True)
    description: Mapped[str] = mapped_column(Text)
    impact: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(160))
    action_required: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(2), default="P0", index=True)
    status: Mapped[str] = mapped_column(String(12), default="OPEN", index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
