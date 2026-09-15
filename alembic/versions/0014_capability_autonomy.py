"""add per-capability autonomy and governance review

Revision ID: 0014_capability_autonomy
Revises: 0013_seed_tool_decisions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_capability_autonomy"
down_revision: str | None = "0013_seed_tool_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "capability_autonomy",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("capability_key", sa.String(length=160), nullable=False),
        sa.Column("autonomy_level", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column("authority_scope", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("constraints", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint(
            "autonomy_level BETWEEN 0 AND 5",
            name=op.f("ck_capability_autonomy_capability_autonomy_level_range"),
        ),
        sa.CheckConstraint(
            "status IN ('proposed','validated','suspended')",
            name=op.f("ck_capability_autonomy_capability_autonomy_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_capability_autonomy_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capability_autonomy")),
        sa.UniqueConstraint(
            "project_id",
            "capability_key",
            name="uq_capability_autonomy_project_capability",
        ),
    )
    for column in ("project_id", "capability_key", "status"):
        op.create_index(
            op.f(f"ix_capability_autonomy_{column}"),
            "capability_autonomy",
            [column],
            unique=False,
        )

    op.create_table(
        "governance_review_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("findings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score BETWEEN 0 AND 100",
            name=op.f("ck_governance_review_snapshots_governance_review_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_governance_review_snapshots_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_governance_review_snapshots"),
        ),
    )
    op.create_index(
        op.f("ix_governance_review_snapshots_project_id"),
        "governance_review_snapshots",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_governance_review_snapshots_computed_at"),
        "governance_review_snapshots",
        ["computed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("governance_review_snapshots")
    op.drop_table("capability_autonomy")
