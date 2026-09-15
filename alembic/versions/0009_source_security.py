"""add governed sources and knowledge security fields

Revision ID: 0009_source_security
Revises: 0008_knowledge_maintenance
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_source_security"
down_revision: str | None = "0008_knowledge_maintenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("base_uri", sa.Text(), nullable=False),
        sa.Column("source_class", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("health_status", sa.String(length=32), nullable=False),
        sa.Column("access_mode", sa.String(length=32), nullable=False),
        sa.Column("trust_score", sa.Integer(), nullable=False),
        sa.Column("approved_for_fetch", sa.Boolean(), nullable=False),
        sa.Column("license_name", sa.String(length=240), nullable=True),
        sa.Column("terms_uri", sa.Text(), nullable=True),
        sa.Column("expected_update_minutes", sa.Integer(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
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
            "source_class IN ('primary','specialized','secondary','aggregator','structural')",
            name=op.f("ck_knowledge_sources_knowledge_source_class_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('candidate','approved','paused','blocked','rejected')",
            name=op.f("ck_knowledge_sources_knowledge_source_status_valid"),
        ),
        sa.CheckConstraint(
            "health_status IN ('unknown','healthy','degraded','unreachable')",
            name=op.f("ck_knowledge_sources_knowledge_source_health_valid"),
        ),
        sa.CheckConstraint(
            "access_mode IN ('public','authorized','manual')",
            name=op.f("ck_knowledge_sources_knowledge_source_access_mode_valid"),
        ),
        sa.CheckConstraint(
            "trust_score BETWEEN 0 AND 100",
            name=op.f("ck_knowledge_sources_knowledge_source_trust_range"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_sources")),
        sa.UniqueConstraint("key", name=op.f("uq_knowledge_sources_key")),
    )
    op.create_index("ix_knowledge_sources_key", "knowledge_sources", ["key"])
    op.create_index(
        "ix_knowledge_sources_status_class",
        "knowledge_sources",
        ["status", "source_class"],
    )

    op.add_column(
        "knowledge_claims",
        sa.Column("source_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "knowledge_claims",
        sa.Column(
            "data_classification",
            sa.String(length=32),
            server_default="internal",
            nullable=False,
        ),
    )
    op.add_column(
        "knowledge_claims",
        sa.Column(
            "security_flags",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        op.f("fk_knowledge_claims_source_id_knowledge_sources"),
        "knowledge_claims",
        "knowledge_sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_knowledge_claims_source_id", "knowledge_claims", ["source_id"])
    op.create_check_constraint(
        op.f("ck_knowledge_claims_knowledge_data_classification_valid"),
        "knowledge_claims",
        "data_classification IN ('public','internal','confidential','restricted')",
    )
    op.alter_column("knowledge_claims", "data_classification", server_default=None)
    op.alter_column("knowledge_claims", "security_flags", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_knowledge_claims_knowledge_data_classification_valid"),
        "knowledge_claims",
        type_="check",
    )
    op.drop_index("ix_knowledge_claims_source_id", table_name="knowledge_claims")
    op.drop_constraint(
        op.f("fk_knowledge_claims_source_id_knowledge_sources"),
        "knowledge_claims",
        type_="foreignkey",
    )
    op.drop_column("knowledge_claims", "security_flags")
    op.drop_column("knowledge_claims", "data_classification")
    op.drop_column("knowledge_claims", "source_id")

    op.drop_index("ix_knowledge_sources_status_class", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_key", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
