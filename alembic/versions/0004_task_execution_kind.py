"""add explicit task execution contract

Revision ID: 0004_task_execution_kind
Revises: 0003_agent_identity
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_task_execution_kind"
down_revision: str | None = "0003_agent_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("execution_kind", sa.String(length=80), nullable=True),
    )
    op.create_check_constraint(
        "ck_tasks_execution_kind_valid",
        "tasks",
        "execution_kind IS NULL OR execution_kind IN ('control_plane_health')",
    )
    op.create_index("ix_tasks_execution_kind", "tasks", ["execution_kind"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tasks_execution_kind", table_name="tasks")
    op.drop_constraint("ck_tasks_execution_kind_valid", "tasks", type_="check")
    op.drop_column("tasks", "execution_kind")
