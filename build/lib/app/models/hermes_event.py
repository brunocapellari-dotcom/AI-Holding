from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HermesEventReceipt(Base):
    __tablename__ = "hermes_event_receipts"
    __table_args__ = (UniqueConstraint("event_id", name="uq_hermes_event_receipts_event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    producer: Mapped[str] = mapped_column(String(160), index=True)
    project_key: Mapped[str] = mapped_column(String(120), index=True)
    schema_version: Mapped[str] = mapped_column(String(32), index=True)
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    causation_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
