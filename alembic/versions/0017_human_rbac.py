"""add fail-closed human RBAC bindings

Revision ID: 0017_human_rbac
Revises: 0016_cloud_sql_iam_connector_decision
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_human_rbac"
down_revision: str | None = "0016_cloud_sql_iam_connector_decision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "human_identity_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("issuer", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
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
            "role IN ('owner','operator','auditor','viewer')",
            name=op.f("ck_human_identity_roles_ck_human_identity_role_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_human_identity_roles")),
        sa.UniqueConstraint(
            "issuer",
            "subject",
            name="uq_human_identity_principal",
        ),
    )
    op.create_index(
        op.f("ix_human_identity_roles_email"),
        "human_identity_roles",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_human_identity_roles_role"),
        "human_identity_roles",
        ["role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("human_identity_roles")
