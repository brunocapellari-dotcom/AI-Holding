"""add collector registry

Revision ID: 0009_collector_registry
Revises: 0008_knowledge_maintenance
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_collector_registry"
down_revision: str | None = "0008_knowledge_maintenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collectors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collector_id", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("collector_type", sa.String(length=80), nullable=False),
        sa.Column("frequency_seconds", sa.Integer(), nullable=True),
        sa.Column("last_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="disabled",
            nullable=False,
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), server_default="0", nullable=False),
        sa.Column("owner_agent_id", sa.Uuid(), nullable=True),
        sa.Column("produced_data", sa.JSON(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('healthy','degraded','failed','disabled')",
            name=op.f("ck_collectors_status_valid"),
        ),
        sa.CheckConstraint(
            "frequency_seconds IS NULL OR frequency_seconds >= 60",
            name=op.f("ck_collectors_frequency_valid"),
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name=op.f("ck_collectors_latency_nonnegative"),
        ),
        sa.CheckConstraint(
            "failure_count >= 0",
            name=op.f("ck_collectors_failure_count_nonnegative"),
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0",
            name=op.f("ck_collectors_consecutive_failures_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_agent_id"],
            ["agents.id"],
            name=op.f("fk_collectors_owner_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collectors")),
        sa.UniqueConstraint("collector_id", name=op.f("uq_collectors_collector_id")),
    )
    op.create_index(
        op.f("ix_collectors_source"),
        "collectors",
        ["source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collectors_collector_type"),
        "collectors",
        ["collector_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collectors_status"),
        "collectors",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_collectors_owner_agent_id"),
        "collectors",
        ["owner_agent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_collectors_owner_agent_id"), table_name="collectors")
    op.drop_index(op.f("ix_collectors_status"), table_name="collectors")
    op.drop_index(op.f("ix_collectors_collector_type"), table_name="collectors")
    op.drop_index(op.f("ix_collectors_source"), table_name="collectors")
    op.drop_table("collectors")
