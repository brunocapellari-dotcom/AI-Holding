"""add explicit autonomous task readiness contract

Revision ID: 0005_task_auto_start
Revises: 0004_task_execution_kind
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_task_auto_start"
down_revision: str | None = "0004_task_execution_kind"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "auto_start",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_check_constraint(
        "ck_tasks_auto_start_requires_execution_kind",
        "tasks",
        "NOT auto_start OR execution_kind IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tasks_auto_start_requires_execution_kind",
        "tasks",
        type_="check",
    )
    op.drop_column("tasks", "auto_start")
