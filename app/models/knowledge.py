from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
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


class EpistemicStatus(StrEnum):
    observed = "observed"
    estimated = "estimated"
    projected = "projected"
    inferred = "inferred"
    structural = "structural"


class KnowledgeLifecycle(StrEnum):
    raw = "raw"
    candidate = "candidate"
    validated = "validated"
    canonical = "canonical"
    superseded = "superseded"


class OutcomeVerdict(StrEnum):
    confirmed = "confirmed"
    partially_confirmed = "partially_confirmed"
    refuted = "refuted"
    inconclusive = "inconclusive"


class KnowledgeClaim(Base, TimestampMixin):
    __tablename__ = "knowledge_claims"
    __table_args__ = (
        UniqueConstraint("namespace", "fingerprint", name="uq_knowledge_namespace_fingerprint"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="knowledge_confidence_range"),
        CheckConstraint(
            "epistemic_status IN ('observed','estimated','projected','inferred','structural')",
            name="knowledge_epistemic_status_valid",
        ),
        CheckConstraint(
            "lifecycle_status IN ('raw','candidate','validated','canonical','superseded')",
            name="knowledge_lifecycle_status_valid",
        ),
        Index("ix_knowledge_context", "namespace", "lifecycle_status", "confidence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    namespace: Mapped[str] = mapped_column(String(120), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    statement: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    epistemic_status: Mapped[str] = mapped_column(String(32), default=EpistemicStatus.structural.value)
    lifecycle_status: Mapped[str] = mapped_column(String(32), default=KnowledgeLifecycle.raw.value)
    confidence: Mapped[int] = mapped_column(Integer, default=50)
    source_name: Mapped[str] = mapped_column(String(240))
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    tags: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("knowledge_claims.id", ondelete="SET NULL"), nullable=True, index=True
    )
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    obsidian_path: Mapped[str | None] = mapped_column(String(500), nullable=True)


class KnowledgeOutcome(Base, TimestampMixin):
    __tablename__ = "knowledge_outcomes"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('confirmed','partially_confirmed','refuted','inconclusive')",
            name="knowledge_outcome_verdict_valid",
        ),
        Index("ix_knowledge_outcomes_claim_created", "claim_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_claims.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    verdict: Mapped[str] = mapped_column(String(32))
    observed_result: Mapped[str] = mapped_column(Text)
    error_metric: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
