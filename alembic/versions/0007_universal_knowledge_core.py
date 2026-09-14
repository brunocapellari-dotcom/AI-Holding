"""add universal knowledge core

Revision ID: 0007_universal_knowledge_core
Revises: 0006_recurring_routines
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_universal_knowledge_core"
down_revision: str | None = "0006_recurring_routines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("namespace", sa.String(length=120), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_agent_id", sa.Uuid(), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("epistemic_status", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=240), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("source_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("supersedes_id", sa.Uuid(), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("obsidian_path", sa.String(length=500), nullable=True),
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
            "confidence BETWEEN 0 AND 100",
            name=op.f("ck_knowledge_claims_knowledge_confidence_range"),
        ),
        sa.CheckConstraint(
            "epistemic_status IN ('observed','estimated','projected','inferred','structural')",
            name=op.f("ck_knowledge_claims_knowledge_epistemic_status_valid"),
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('raw','candidate','validated','canonical','superseded')",
            name=op.f("ck_knowledge_claims_knowledge_lifecycle_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_agent_id"],
            ["agents.id"],
            name=op.f("fk_knowledge_claims_created_by_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_knowledge_claims_project_id_projects"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_id"],
            ["knowledge_claims.id"],
            name=op.f("fk_knowledge_claims_supersedes_id_knowledge_claims"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_claims")),
        sa.UniqueConstraint(
            "namespace",
            "fingerprint",
            name="uq_knowledge_namespace_fingerprint",
        ),
    )
    op.create_index("ix_knowledge_claims_namespace", "knowledge_claims", ["namespace"])
    op.create_index("ix_knowledge_claims_project_id", "knowledge_claims", ["project_id"])
    op.create_index(
        "ix_knowledge_claims_created_by_agent_id",
        "knowledge_claims",
        ["created_by_agent_id"],
    )
    op.create_index("ix_knowledge_claims_fingerprint", "knowledge_claims", ["fingerprint"])
    op.create_index("ix_knowledge_claims_supersedes_id", "knowledge_claims", ["supersedes_id"])
    op.create_index(
        "ix_knowledge_context",
        "knowledge_claims",
        ["namespace", "lifecycle_status", "confidence"],
    )

    op.create_table(
        "knowledge_outcomes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_agent_id", sa.Uuid(), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("observed_result", sa.Text(), nullable=False),
        sa.Column("error_metric", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
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
            "verdict IN ('confirmed','partially_confirmed','refuted','inconclusive')",
            name=op.f("ck_knowledge_outcomes_knowledge_outcome_verdict_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["knowledge_claims.id"],
            name=op.f("fk_knowledge_outcomes_claim_id_knowledge_claims"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_agent_id"],
            ["agents.id"],
            name=op.f("fk_knowledge_outcomes_created_by_agent_id_agents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_knowledge_outcomes_project_id_projects"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_outcomes")),
    )
    op.create_index("ix_knowledge_outcomes_claim_id", "knowledge_outcomes", ["claim_id"])
    op.create_index("ix_knowledge_outcomes_project_id", "knowledge_outcomes", ["project_id"])
    op.create_index(
        "ix_knowledge_outcomes_created_by_agent_id",
        "knowledge_outcomes",
        ["created_by_agent_id"],
    )
    op.create_index(
        "ix_knowledge_outcomes_claim_created",
        "knowledge_outcomes",
        ["claim_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_outcomes_claim_created", table_name="knowledge_outcomes")
    op.drop_index("ix_knowledge_outcomes_created_by_agent_id", table_name="knowledge_outcomes")
    op.drop_index("ix_knowledge_outcomes_project_id", table_name="knowledge_outcomes")
    op.drop_index("ix_knowledge_outcomes_claim_id", table_name="knowledge_outcomes")
    op.drop_table("knowledge_outcomes")

    op.drop_index("ix_knowledge_context", table_name="knowledge_claims")
    op.drop_index("ix_knowledge_claims_supersedes_id", table_name="knowledge_claims")
    op.drop_index("ix_knowledge_claims_fingerprint", table_name="knowledge_claims")
    op.drop_index("ix_knowledge_claims_created_by_agent_id", table_name="knowledge_claims")
    op.drop_index("ix_knowledge_claims_project_id", table_name="knowledge_claims")
    op.drop_index("ix_knowledge_claims_namespace", table_name="knowledge_claims")
    op.drop_table("knowledge_claims")
