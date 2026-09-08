"""add canonical agent identity bindings

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
    op.create_table(
        "agent_identities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
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
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", name="uq_agent_identity_agent"),
        sa.UniqueConstraint("issuer", "subject", name="uq_agent_identity_principal"),
    )
    op.create_index(
        "ix_agent_identities_agent_id",
        "agent_identities",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_identities_email",
        "agent_identities",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_identities_email", table_name="agent_identities")
    op.drop_index("ix_agent_identities_agent_id", table_name="agent_identities")
    op.drop_table("agent_identities")
