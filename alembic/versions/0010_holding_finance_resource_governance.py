"""add holding finance resource and architecture governance

Revision ID: 0010_holding_finance_resource
Revises: 0009_holding_operating_system
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_holding_finance_resource"
down_revision: str | None = "0009_holding_operating_system"
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


def _json_object_column(name: str) -> sa.Column[object]:
    return sa.Column(
        name,
        sa.JSON(),
        nullable=False,
        server_default=sa.text("'{}'"),
    )


def _json_list_column(name: str) -> sa.Column[object]:
    return sa.Column(
        name,
        sa.JSON(),
        nullable=False,
        server_default=sa.text("'[]'"),
    )


def upgrade() -> None:
    op.create_table(
        "revenue_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("amount_micros", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        _json_object_column("metadata_json"),
        sa.CheckConstraint(
            "amount_micros >= 0",
            name=op.f("ck_revenue_entries_revenue_amount_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_revenue_entries_project_id_projects"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_revenue_entries")),
    )
    for column in ("project_id", "source", "observed_at"):
        op.create_index(
            op.f(f"ix_revenue_entries_{column}"),
            "revenue_entries",
            [column],
            unique=False,
        )

    op.create_table(
        "financial_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revenue_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("budget_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runway_days", sa.Integer(), nullable=True),
        sa.Column("payback_days", sa.Integer(), nullable=True),
        sa.Column("roi_estimate_bps", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        _json_list_column("assumptions"),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "revenue_micros >= 0",
            name=op.f("ck_financial_snapshots_financial_revenue_nonnegative"),
        ),
        sa.CheckConstraint(
            "cost_micros >= 0",
            name=op.f("ck_financial_snapshots_financial_cost_nonnegative"),
        ),
        sa.CheckConstraint(
            "budget_micros >= 0",
            name=op.f("ck_financial_snapshots_financial_budget_nonnegative"),
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100",
            name=op.f("ck_financial_snapshots_financial_confidence_range"),
        ),
        sa.CheckConstraint(
            "runway_days IS NULL OR runway_days >= 0",
            name=op.f("ck_financial_snapshots_runway_nonnegative"),
        ),
        sa.CheckConstraint(
            "payback_days IS NULL OR payback_days >= 0",
            name=op.f("ck_financial_snapshots_payback_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_financial_snapshots_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_financial_snapshots")),
    )
    for column in ("project_id", "period_start", "period_end", "computed_at"):
        op.create_index(
            op.f(f"ix_financial_snapshots_{column}"),
            "financial_snapshots",
            [column],
            unique=False,
        )

    op.create_table(
        "resource_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("resource_type", sa.String(length=24), nullable=False),
        sa.Column("resource_key", sa.String(length=160), nullable=False),
        sa.Column("requested_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allocated_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit", sa.String(length=40), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="proposed",
        ),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        _json_object_column("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "resource_type IN "
            "('cpu','gpu','storage','agent','model','budget','developer')",
            name=op.f("ck_resource_allocations_resource_type_valid"),
        ),
        sa.CheckConstraint(
            "requested_units >= 0",
            name=op.f("ck_resource_allocations_requested_units_nonnegative"),
        ),
        sa.CheckConstraint(
            "allocated_units >= 0",
            name=op.f("ck_resource_allocations_allocated_units_nonnegative"),
        ),
        sa.CheckConstraint(
            "status IN ('proposed','approved','active','reduced','released','rejected')",
            name=op.f("ck_resource_allocations_resource_allocation_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_resource_allocations_project_id_projects"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_resource_allocations")),
    )
    for column in ("project_id", "resource_type", "status"):
        op.create_index(
            op.f(f"ix_resource_allocations_{column}"),
            "resource_allocations",
            [column],
            unique=False,
        )

    op.create_table(
        "portfolio_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("value_score", sa.Integer(), nullable=False),
        sa.Column("progress_score", sa.Integer(), nullable=False),
        sa.Column("cost_score", sa.Integer(), nullable=False),
        sa.Column("complexity_score", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("monetization_score", sa.Integer(), nullable=False),
        sa.Column("dependency_score", sa.Integer(), nullable=False),
        sa.Column(
            "requires_owner_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("rationale", sa.Text(), nullable=False),
        _json_list_column("evidence"),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "classification IN ('accelerate','maintain','restructure','pause','sunset')",
            name=op.f("ck_portfolio_reviews_portfolio_classification_valid"),
        ),
        sa.CheckConstraint(
            "value_score BETWEEN 0 AND 100",
            name=op.f("ck_portfolio_reviews_value_score_range"),
        ),
        sa.CheckConstraint(
            "progress_score BETWEEN 0 AND 100",
            name=op.f("ck_portfolio_reviews_progress_score_range"),
        ),
        sa.CheckConstraint(
            "cost_score BETWEEN 0 AND 100",
            name=op.f("ck_portfolio_reviews_cost_score_range"),
        ),
        sa.CheckConstraint(
            "complexity_score BETWEEN 0 AND 100",
            name=op.f("ck_portfolio_reviews_complexity_score_range"),
        ),
        sa.CheckConstraint(
            "risk_score BETWEEN 0 AND 100",
            name=op.f("ck_portfolio_reviews_risk_score_range"),
        ),
        sa.CheckConstraint(
            "monetization_score BETWEEN 0 AND 100",
            name=op.f("ck_portfolio_reviews_monetization_score_range"),
        ),
        sa.CheckConstraint(
            "dependency_score BETWEEN 0 AND 100",
            name=op.f("ck_portfolio_reviews_dependency_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_portfolio_reviews_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_portfolio_reviews")),
    )
    for column in ("project_id", "classification", "reviewed_at"):
        op.create_index(
            op.f(f"ix_portfolio_reviews_{column}"),
            "portfolio_reviews",
            [column],
            unique=False,
        )

    op.create_table(
        "tool_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("tool_name", sa.String(length=160), nullable=False),
        sa.Column("capability", sa.String(length=160), nullable=False),
        sa.Column("classification", sa.String(length=20), nullable=False),
        sa.Column("replaces_key", sa.String(length=120), nullable=True),
        sa.Column("benefit", sa.Text(), nullable=False, server_default=""),
        sa.Column("maintenance_cost", sa.Text(), nullable=False, server_default=""),
        sa.Column("license", sa.String(length=120), nullable=False, server_default="unknown"),
        sa.Column("risk", sa.Text(), nullable=False, server_default=""),
        sa.Column("rationale", sa.Text(), nullable=False),
        _json_list_column("evidence"),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "classification IN ('adopt','replace','benchmark','reserve','reject')",
            name=op.f("ck_tool_decisions_tool_classification_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_decisions")),
        sa.UniqueConstraint("key", name="uq_tool_decision_key"),
    )
    for column in ("key", "tool_name", "classification", "reviewed_at"):
        op.create_index(
            op.f(f"ix_tool_decisions_{column}"),
            "tool_decisions",
            [column],
            unique=False,
        )


def downgrade() -> None:
    op.drop_table("tool_decisions")
    op.drop_table("portfolio_reviews")
    op.drop_table("resource_allocations")
    op.drop_table("financial_snapshots")
    op.drop_table("revenue_entries")
