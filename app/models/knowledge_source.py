from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.entities import TimestampMixin


class SourceClass(StrEnum):
    primary = "primary"
    specialized = "specialized"
    secondary = "secondary"
    aggregator = "aggregator"
    structural = "structural"


class SourceStatus(StrEnum):
    candidate = "candidate"
    approved = "approved"
    paused = "paused"
    blocked = "blocked"
    rejected = "rejected"


class SourceHealth(StrEnum):
    unknown = "unknown"
    healthy = "healthy"
    degraded = "degraded"
    unreachable = "unreachable"


class SourceAccessMode(StrEnum):
    public = "public"
    authorized = "authorized"
    manual = "manual"


class KnowledgeSource(Base, TimestampMixin):
    __tablename__ = "knowledge_sources"
    __table_args__ = (
        CheckConstraint(
            "source_class IN ('primary','specialized','secondary','aggregator','structural')",
            name="knowledge_source_class_valid",
        ),
        CheckConstraint(
            "status IN ('candidate','approved','paused','blocked','rejected')",
            name="knowledge_source_status_valid",
        ),
        CheckConstraint(
            "health_status IN ('unknown','healthy','degraded','unreachable')",
            name="knowledge_source_health_valid",
        ),
        CheckConstraint(
            "access_mode IN ('public','authorized','manual')",
            name="knowledge_source_access_mode_valid",
        ),
        CheckConstraint(
            "trust_score BETWEEN 0 AND 100",
            name="knowledge_source_trust_range",
        ),
        Index("ix_knowledge_sources_status_class", "status", "source_class"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240))
    base_uri: Mapped[str] = mapped_column(Text)
    source_class: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default=SourceStatus.candidate.value)
    health_status: Mapped[str] = mapped_column(
        String(32), default=SourceHealth.unknown.value
    )
    access_mode: Mapped[str] = mapped_column(
        String(32), default=SourceAccessMode.public.value
    )
    trust_score: Mapped[int] = mapped_column(Integer, default=50)
    approved_for_fetch: Mapped[bool] = mapped_column(Boolean, default=False)
    license_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    terms_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_update_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
