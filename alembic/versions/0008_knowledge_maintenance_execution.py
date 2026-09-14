"""add knowledge maintenance execution kinds

Revision ID: 0008_knowledge_maintenance
Revises: 0007_universal_knowledge_core
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_knowledge_maintenance"
down_revision: str | None = "0007_universal_knowledge_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXECUTION_KIND_CHECK = (
    "execution_kind IS NULL OR execution_kind IN "
    "('control_plane_health','knowledge_gap_scan','knowledge_outcome_review')"
)
ROUTINE_EXECUTION_KIND_CHECK = (
    "execution_kind IN ('control_plane_health','knowledge_gap_scan','knowledge_outcome_review')"
)


def upgrade() -> None:
    op.drop_constraint("ck_tasks_execution_kind_valid", "tasks", type_="check")
    op.create_check_constraint(
        "ck_tasks_execution_kind_valid",
        "tasks",
        EXECUTION_KIND_CHECK,
    )
    op.drop_constraint(op.f("ck_routines_execution_kind_valid"), "routines", type_="check")
    op.create_check_constraint(
        op.f("ck_routines_execution_kind_valid"),
        "routines",
        ROUTINE_EXECUTION_KIND_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_routines_execution_kind_valid"), "routines", type_="check")
    op.create_check_constraint(
        op.f("ck_routines_execution_kind_valid"),
        "routines",
        "execution_kind IN ('control_plane_health')",
    )
    op.drop_constraint("ck_tasks_execution_kind_valid", "tasks", type_="check")
    op.create_check_constraint(
        "ck_tasks_execution_kind_valid",
        "tasks",
        "execution_kind IS NULL OR execution_kind IN ('control_plane_health')",
    )
