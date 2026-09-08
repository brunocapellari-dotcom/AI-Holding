"""add canonical agent identity binding

Revision ID: 0002_agent_identity
Revises: 0001_control_plane_core
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_agent_identity"
down_revision: str | None = "0001_control_plane_core"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("identity_subject", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column("identity_email", sa.String(length=320), nullable=True),
    )
    op.create_index(
        "ix_agents_identity_subject",
        "agents",
        ["identity_subject"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_agents_identity_subject", table_name="agents")
    op.drop_column("agents", "identity_email")
    op.drop_column("agents", "identity_subject")
