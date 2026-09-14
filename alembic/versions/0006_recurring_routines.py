"""add recurring PMO routines

Revision ID: 0006_recurring_routines
Revises: 0005_task_auto_start
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_recurring_routines"
down_revision: str | None = "0005_task_auto_start"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "routines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("execution_kind", sa.String(length=80), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("assigned_agent_id", sa.Uuid(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "execution_kind IN ('control_plane_health')",
            name=op.f("ck_routines_execution_kind_valid"),
        ),
        sa.CheckConstraint(
            "interval_minutes BETWEEN 5 AND 10080",
            name=op.f("ck_routines_interval_minutes_range"),
        ),
        sa.CheckConstraint(
            "priority BETWEEN 0 AND 5",
            name=op.f("ck_routines_priority_range"),
        ),
        sa.ForeignKeyConstraint(
            ["assigned_agent_id"],
            ["agents.id"],
            name=op.f("fk_routines_assigned_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_routines_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routines")),
        sa.UniqueConstraint("project_id", "key", name="uq_routines_project_key"),
    )
    op.create_index(
        "ix_routines_assigned_agent_id",
        "routines",
        ["assigned_agent_id"],
        unique=False,
    )
    op.create_index("ix_routines_due", "routines", ["enabled", "next_due_at"], unique=False)
    op.create_index(
        "ix_routines_execution_kind",
        "routines",
        ["execution_kind"],
        unique=False,
    )
    op.create_index("ix_routines_project_id", "routines", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_routines_project_id", table_name="routines")
    op.drop_index("ix_routines_execution_kind", table_name="routines")
    op.drop_index("ix_routines_due", table_name="routines")
    op.drop_index("ix_routines_assigned_agent_id", table_name="routines")
    op.drop_table("routines")
