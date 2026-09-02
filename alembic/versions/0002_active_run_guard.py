"""enforce one active run per task

Revision ID: 0002_active_run_guard
Revises: 0001_control_plane_core
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_active_run_guard"
down_revision: str | None = "0001_control_plane_core"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_runs_one_active_per_task",
        "runs",
        ["task_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_runs_one_active_per_task", table_name="runs")
