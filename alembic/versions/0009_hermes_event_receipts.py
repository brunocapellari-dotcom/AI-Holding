"""add Hermes operational event receipts

Revision ID: 0009_hermes_event_receipts
Revises: 0008_knowledge_maintenance
Create Date: 2026-10-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_hermes_event_receipts"
down_revision: str | None = "0008_knowledge_maintenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hermes_event_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("producer", sa.String(length=160), nullable=False),
        sa.Column("project_key", sa.String(length=120), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("causation_id", sa.String(length=128), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_hermes_event_receipts_event_id"),
    )
    for column in (
        "event_id",
        "event_type",
        "producer",
        "project_key",
        "schema_version",
        "correlation_id",
        "causation_id",
        "occurred_at",
        "received_at",
    ):
        op.create_index(f"ix_hermes_event_receipts_{column}", "hermes_event_receipts", [column])


def downgrade() -> None:
    op.drop_table("hermes_event_receipts")
