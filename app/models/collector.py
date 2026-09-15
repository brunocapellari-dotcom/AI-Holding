from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CollectorStatus(StrEnum):
    healthy = "healthy"
    degraded = "degraded"
    failed = "failed"
    disabled = "disabled"


class Collector(Base):
    __tablename__ = "collectors"
    __table_args__ = (
        CheckConstraint(
            "status IN ('healthy','degraded','failed','disabled')",
            name="status_valid",
        ),
        CheckConstraint(
            "frequency_seconds IS NULL OR frequency_seconds >= 60",
            name="frequency_valid",
        ),
        CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="latency_nonnegative",
        ),
        CheckConstraint("failure_count >= 0", name="failure_count_nonnegative"),
        CheckConstraint(
            "consecutive_failures >= 0",
            name="consecutive_failures_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    collector_id: Mapped[str] = mapped_column(String(100), unique=True)
    source: Mapped[str] = mapped_column(String(160), index=True)
    collector_type: Mapped[str] = mapped_column(String(80), index=True)
    frequency_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CollectorStatus.disabled.value,
        server_default=CollectorStatus.disabled.value,
        index=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    owner_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    produced_data: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
