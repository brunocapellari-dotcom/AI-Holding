"""add collector execution history and security findings

Revision ID: 0011_holding_evidence_security
Revises: 0010_holding_finance_resource
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_holding_evidence_security"
down_revision: str | None = "0010_holding_finance_resource"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collector_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collector_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_cursor", sa.String(length=500), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("records_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_class", sa.String(length=160), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.CheckConstraint(
            "status IN ('running','success','degraded','failure')",
            name=op.f("ck_collector_executions_collector_execution_status_valid"),
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name=op.f("ck_collector_executions_collector_execution_latency_nonnegative"),
        ),
        sa.CheckConstraint(
            "records_seen >= 0",
            name=op.f("ck_collector_executions_collector_execution_records_seen_nonnegative"),
        ),
        sa.CheckConstraint(
            "records_written >= 0",
            name=op.f("ck_collector_executions_collector_execution_records_written_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["collector_id"],
            ["collector_registry.id"],
            name=op.f("fk_collector_executions_collector_id_collector_registry"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collector_executions")),
    )
    for column in ("collector_id", "status", "started_at"):
        op.create_index(
            op.f(f"ix_collector_executions_{column}"),
            "collector_executions",
            [column],
            unique=False,
        )

    op.create_table(
        "security_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
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
            "severity IN ('info','low','medium','high','critical')",
            name=op.f("ck_security_findings_security_finding_severity_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('open','mitigating','accepted','resolved','false_positive')",
            name=op.f("ck_security_findings_security_finding_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_security_findings_project_id_projects"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_security_findings")),
    )
    for column in ("project_id", "source", "category", "severity", "status", "detected_at"):
        op.create_index(
            op.f(f"ix_security_findings_{column}"),
            "security_findings",
            [column],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("security_findings")
    op.drop_table("collector_executions")
