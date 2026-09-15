from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.entities import TimestampMixin


class CollectorExecution(Base):
    __tablename__ = "collector_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','success','degraded','failure')",
            name="collector_execution_status_valid",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="collector_execution_latency_nonnegative",
        ),
        CheckConstraint(
            "records_seen >= 0",
            name="collector_execution_records_seen_nonnegative",
        ),
        CheckConstraint(
            "records_written >= 0",
            name="collector_execution_records_written_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collector_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("collector_registry.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(20), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_cursor: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    records_written: Mapped[int] = mapped_column(Integer, default=0)
    error_class: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class SecurityFinding(Base, TimestampMixin):
    __tablename__ = "security_findings"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info','low','medium','high','critical')",
            name="security_finding_severity_valid",
        ),
        CheckConstraint(
            "status IN ('open','mitigating','accepted','resolved','false_positive')",
            name="security_finding_status_valid",
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
    source: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    remediation: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
