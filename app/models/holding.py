from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
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


class ProjectOperationalProfile(Base, TimestampMixin):
    __tablename__ = "project_operational_profiles"
    __table_args__ = (
        CheckConstraint(
            "operational_status IN "
            "('planned','ready','running','completed','failed','blocked','paused','cancelled')",
            name="operational_status_valid",
        ),
        CheckConstraint(
            "security_level IN ('public','internal','confidential','restricted')",
            name="security_level_valid",
        ),
        CheckConstraint("budget_micros >= 0", name="budget_nonnegative"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    mission: Mapped[str] = mapped_column(Text, default="")
    operational_status: Mapped[str] = mapped_column(
        String(24), default="planned", index=True
    )
    knowledge_namespace: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_phase: Mapped[str | None] = mapped_column(String(160), nullable=True)
    security_level: Mapped[str] = mapped_column(String(24), default="internal")
    budget_micros: Mapped[int] = mapped_column(Integer, default=0)
    budget_currency: Mapped[str] = mapped_column(String(3), default="BRL")
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class CollectorRegistration(Base, TimestampMixin):
    __tablename__ = "collector_registry"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_collector_project_key"),
        CheckConstraint("frequency_seconds > 0", name="frequency_positive"),
        CheckConstraint("freshness_sla_seconds > 0", name="freshness_positive"),
        CheckConstraint(
            "consecutive_failures >= 0", name="collector_failures_nonnegative"
        ),
        CheckConstraint(
            "status IN ('healthy','degraded','failing','disabled')",
            name="collector_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    key: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(240))
    data_type: Mapped[str] = mapped_column(String(120))
    frequency_seconds: Mapped[int] = mapped_column(Integer)
    freshness_sla_seconds: Mapped[int] = mapped_column(Integer)
    retry_policy: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="degraded", index=True)
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class ProjectHealthSnapshot(Base):
    __tablename__ = "project_health_snapshots"
    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 100", name="health_score_range"),
        CheckConstraint(
            "state IN ('healthy','degraded','at_risk','blocked','offline')",
            name="health_state_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    state: Mapped[str] = mapped_column(String(24), index=True)
    score: Mapped[int] = mapped_column(Integer)
    dimensions: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    reasons: Mapped[list[object]] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class RiskRegisterEntry(Base, TimestampMixin):
    __tablename__ = "risk_registry"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_risk_project_key"),
        CheckConstraint("probability BETWEEN 0 AND 100", name="risk_probability_range"),
        CheckConstraint("impact BETWEEN 1 AND 5", name="risk_impact_range"),
        CheckConstraint(
            "severity IN ('low','medium','high','critical')",
            name="risk_severity_valid",
        ),
        CheckConstraint(
            "status IN ('open','mitigating','accepted','resolved')",
            name="risk_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    probability: Mapped[int] = mapped_column(Integer)
    impact: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    mitigation: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(160), default="risk-ai")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    date_detected: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_review: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class CostEntry(Base):
    __tablename__ = "cost_entries"
    __table_args__ = (
        CheckConstraint("amount_micros >= 0", name="cost_amount_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    amount_micros: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    units: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class RevenueEntry(Base):
    __tablename__ = "revenue_entries"
    __table_args__ = (
        CheckConstraint("amount_micros >= 0", name="revenue_amount_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(160), index=True)
    amount_micros: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"
    __table_args__ = (
        CheckConstraint("revenue_micros >= 0", name="financial_revenue_nonnegative"),
        CheckConstraint("cost_micros >= 0", name="financial_cost_nonnegative"),
        CheckConstraint("budget_micros >= 0", name="financial_budget_nonnegative"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="financial_confidence_range"),
        CheckConstraint("runway_days IS NULL OR runway_days >= 0", name="runway_nonnegative"),
        CheckConstraint(
            "payback_days IS NULL OR payback_days >= 0", name="payback_nonnegative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revenue_micros: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(Integer, default=0)
    budget_micros: Mapped[int] = mapped_column(Integer, default=0)
    runway_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payback_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    roi_estimate_bps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    assumptions: Mapped[list[object]] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class DependencyEdge(Base, TimestampMixin):
    __tablename__ = "dependency_edges"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_key",
            "target_type",
            "target_key",
            name="uq_dependency_edge",
        ),
        CheckConstraint("criticality BETWEEN 1 AND 5", name="dependency_criticality_range"),
        CheckConstraint(
            "source_type IN "
            "('project','service','data','api','agent','skill','model','infrastructure')",
            name="dependency_source_type_valid",
        ),
        CheckConstraint(
            "target_type IN "
            "('project','service','data','api','agent','skill','model','infrastructure')",
            name="dependency_target_type_valid",
        ),
        CheckConstraint(
            "status IN ('healthy','degraded','blocked','offline')",
            name="dependency_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(String(24), index=True)
    source_key: Mapped[str] = mapped_column(String(200), index=True)
    target_type: Mapped[str] = mapped_column(String(24), index=True)
    target_key: Mapped[str] = mapped_column(String(200), index=True)
    criticality: Mapped[int] = mapped_column(Integer, default=3)
    blocking: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(24), default="healthy", index=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class HoldingAlert(Base, TimestampMixin):
    __tablename__ = "holding_alerts"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_alert_dedupe_key"),
        CheckConstraint(
            "level IN ('info','watch','action_required','critical')",
            name="alert_level_valid",
        ),
        CheckConstraint("status IN ('active','resolved')", name="alert_status_valid"),
        CheckConstraint("occurrences >= 1", name="alert_occurrences_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(24), index=True)
    source: Mapped[str] = mapped_column(String(120), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(220))
    title: Mapped[str] = mapped_column(String(240))
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class IntegrationState(Base, TimestampMixin):
    __tablename__ = "integration_states"
    __table_args__ = (
        UniqueConstraint("service_key", name="uq_integration_service_key"),
        CheckConstraint(
            "status IN ('healthy','degraded','blocked','offline','unconfigured')",
            name="integration_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    service_key: Mapped[str] = mapped_column(String(100), index=True)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(
        String(24), default="unconfigured", index=True
    )
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    freshness_sla_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class VentureEvaluation(Base, TimestampMixin):
    __tablename__ = "venture_evaluations"
    __table_args__ = (
        UniqueConstraint("key", name="uq_venture_key"),
        CheckConstraint("automation_pct BETWEEN 0 AND 100", name="venture_automation_range"),
        CheckConstraint(
            "validation_cost_micros >= 0",
            name="venture_validation_cost_nonnegative",
        ),
        CheckConstraint(
            "decision IN ('research','build','hold','reject')",
            name="venture_decision_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(220))
    stage: Mapped[str] = mapped_column(String(80), default="idea")
    automation_pct: Mapped[int] = mapped_column(Integer, default=0)
    unit_economics: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    risk_summary: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    validation_cost_micros: Mapped[int] = mapped_column(Integer, default=0)
    decision: Mapped[str] = mapped_column(String(20), default="research", index=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)


class ResourceAllocationEntry(Base, TimestampMixin):
    __tablename__ = "resource_allocations"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN "
            "('cpu','gpu','storage','agent','model','budget','developer')",
            name="resource_type_valid",
        ),
        CheckConstraint("requested_units >= 0", name="requested_units_nonnegative"),
        CheckConstraint("allocated_units >= 0", name="allocated_units_nonnegative"),
        CheckConstraint(
            "status IN ('proposed','approved','active','reduced','released','rejected')",
            name="resource_allocation_status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    resource_type: Mapped[str] = mapped_column(String(24), index=True)
    resource_key: Mapped[str] = mapped_column(String(160))
    requested_units: Mapped[int] = mapped_column(Integer, default=0)
    allocated_units: Mapped[int] = mapped_column(Integer, default=0)
    unit: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class PortfolioReview(Base, TimestampMixin):
    __tablename__ = "portfolio_reviews"
    __table_args__ = (
        CheckConstraint(
            "classification IN ('accelerate','maintain','restructure','pause','sunset')",
            name="portfolio_classification_valid",
        ),
        CheckConstraint("value_score BETWEEN 0 AND 100", name="value_score_range"),
        CheckConstraint("progress_score BETWEEN 0 AND 100", name="progress_score_range"),
        CheckConstraint("cost_score BETWEEN 0 AND 100", name="cost_score_range"),
        CheckConstraint(
            "complexity_score BETWEEN 0 AND 100", name="complexity_score_range"
        ),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        CheckConstraint(
            "monetization_score BETWEEN 0 AND 100", name="monetization_score_range"
        ),
        CheckConstraint(
            "dependency_score BETWEEN 0 AND 100", name="dependency_score_range"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
    )
    classification: Mapped[str] = mapped_column(String(20), index=True)
    value_score: Mapped[int] = mapped_column(Integer)
    progress_score: Mapped[int] = mapped_column(Integer)
    cost_score: Mapped[int] = mapped_column(Integer)
    complexity_score: Mapped[int] = mapped_column(Integer)
    risk_score: Mapped[int] = mapped_column(Integer)
    monetization_score: Mapped[int] = mapped_column(Integer)
    dependency_score: Mapped[int] = mapped_column(Integer)
    requires_owner_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ToolDecision(Base, TimestampMixin):
    __tablename__ = "tool_decisions"
    __table_args__ = (
        UniqueConstraint("key", name="uq_tool_decision_key"),
        CheckConstraint(
            "classification IN ('adopt','replace','benchmark','reserve','reject')",
            name="tool_classification_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(120), index=True)
    tool_name: Mapped[str] = mapped_column(String(160), index=True)
    capability: Mapped[str] = mapped_column(String(160))
    classification: Mapped[str] = mapped_column(String(20), index=True)
    replaces_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    benefit: Mapped[str] = mapped_column(Text, default="")
    maintenance_cost: Mapped[str] = mapped_column(Text, default="")
    license: Mapped[str] = mapped_column(String(120), default="unknown")
    risk: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
