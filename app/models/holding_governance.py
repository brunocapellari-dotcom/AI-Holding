from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.entities import TimestampMixin


class CapabilityAutonomy(Base, TimestampMixin):
    __tablename__ = "capability_autonomy"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "capability_key",
            name="uq_capability_autonomy_project_capability",
        ),
        CheckConstraint(
            "autonomy_level BETWEEN 0 AND 5",
            name="capability_autonomy_level_range",
        ),
        CheckConstraint(
            "status IN ('proposed','validated','suspended')",
            name="capability_autonomy_status_valid",
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
    capability_key: Mapped[str] = mapped_column(String(160), index=True)
    autonomy_level: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="proposed", index=True)
    authority_scope: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    constraints: Mapped[list[object]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)


class GovernanceReviewSnapshot(Base):
    __tablename__ = "governance_review_snapshots"
    __table_args__ = (
        CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="governance_review_score_range",
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
    score: Mapped[int] = mapped_column(Integer)
    findings: Mapped[list[object]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[object]] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
