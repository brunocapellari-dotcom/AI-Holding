"""add holding operating system registries

Revision ID: 0009_holding_operating_system
Revises: 0008_knowledge_maintenance
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_holding_operating_system"
down_revision: str | None = "0008_knowledge_maintenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "project_operational_profiles",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("mission", sa.Text(), nullable=False, server_default=""),
        sa.Column("operational_status", sa.String(length=24), nullable=False, server_default="planned"),
        sa.Column("knowledge_namespace", sa.String(length=200), nullable=True),
        sa.Column("current_phase", sa.String(length=160), nullable=True),
        sa.Column("security_level", sa.String(length=24), nullable=False, server_default="internal"),
        sa.Column("budget_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("budget_currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint(
            "operational_status IN ('planned','ready','running','completed','failed','blocked','paused','cancelled')",
            name=op.f("ck_project_operational_profiles_operational_status_valid"),
        ),
        sa.CheckConstraint(
            "security_level IN ('public','internal','confidential','restricted')",
            name=op.f("ck_project_operational_profiles_security_level_valid"),
        ),
        sa.CheckConstraint(
            "budget_micros >= 0", name=op.f("ck_project_operational_profiles_budget_nonnegative")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_project_operational_profiles_project_id_projects"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("project_id", name=op.f("pk_project_operational_profiles")),
    )
    op.create_index(
        op.f("ix_project_operational_profiles_operational_status"),
        "project_operational_profiles",
        ["operational_status"],
        unique=False,
    )

    op.create_table(
        "collector_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=240), nullable=False),
        sa.Column("data_type", sa.String(length=120), nullable=False),
        sa.Column("frequency_seconds", sa.Integer(), nullable=False),
        sa.Column("freshness_sla_seconds", sa.Integer(), nullable=False),
        sa.Column("retry_policy", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="degraded"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_latency_ms", sa.Integer(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint("frequency_seconds > 0", name=op.f("ck_collector_registry_frequency_positive")),
        sa.CheckConstraint(
            "freshness_sla_seconds > 0", name=op.f("ck_collector_registry_freshness_positive")
        ),
        sa.CheckConstraint(
            "consecutive_failures >= 0", name=op.f("ck_collector_registry_collector_failures_nonnegative")
        ),
        sa.CheckConstraint(
            "status IN ('healthy','degraded','failing','disabled')",
            name=op.f("ck_collector_registry_collector_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_collector_registry_project_id_projects"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_collector_registry")),
        sa.UniqueConstraint("project_id", "key", name="uq_collector_project_key"),
    )
    op.create_index(op.f("ix_collector_registry_project_id"), "collector_registry", ["project_id"], unique=False)
    op.create_index(op.f("ix_collector_registry_status"), "collector_registry", ["status"], unique=False)

    op.create_table(
        "project_health_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=24), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("dimensions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name=op.f("ck_project_health_snapshots_health_score_range")),
        sa.CheckConstraint(
            "state IN ('healthy','degraded','at_risk','blocked','offline')",
            name=op.f("ck_project_health_snapshots_health_state_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_project_health_snapshots_project_id_projects"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_project_health_snapshots")),
    )
    op.create_index(op.f("ix_project_health_snapshots_project_id"), "project_health_snapshots", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_health_snapshots_state"), "project_health_snapshots", ["state"], unique=False)
    op.create_index(op.f("ix_project_health_snapshots_computed_at"), "project_health_snapshots", ["computed_at"], unique=False)

    op.create_table(
        "risk_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner", sa.String(length=160), nullable=False, server_default="risk-ai"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("date_detected", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_review", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint("probability BETWEEN 0 AND 100", name=op.f("ck_risk_registry_risk_probability_range")),
        sa.CheckConstraint("impact BETWEEN 1 AND 5", name=op.f("ck_risk_registry_risk_impact_range")),
        sa.CheckConstraint(
            "severity IN ('low','medium','high','critical')", name=op.f("ck_risk_registry_risk_severity_valid")
        ),
        sa.CheckConstraint(
            "status IN ('open','mitigating','accepted','resolved')", name=op.f("ck_risk_registry_risk_status_valid")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_risk_registry_project_id_projects"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_registry")),
        sa.UniqueConstraint("project_id", "key", name="uq_risk_project_key"),
    )
    op.create_index(op.f("ix_risk_registry_project_id"), "risk_registry", ["project_id"], unique=False)
    op.create_index(op.f("ix_risk_registry_severity"), "risk_registry", ["severity"], unique=False)
    op.create_index(op.f("ix_risk_registry_status"), "risk_registry", ["status"], unique=False)

    op.create_table(
        "cost_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("amount_micros", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="BRL"),
        sa.Column("units", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.CheckConstraint("amount_micros >= 0", name=op.f("ck_cost_entries_cost_amount_nonnegative")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_cost_entries_project_id_projects"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cost_entries")),
    )
    op.create_index(op.f("ix_cost_entries_project_id"), "cost_entries", ["project_id"], unique=False)
    op.create_index(op.f("ix_cost_entries_provider"), "cost_entries", ["provider"], unique=False)
    op.create_index(op.f("ix_cost_entries_category"), "cost_entries", ["category"], unique=False)
    op.create_index(op.f("ix_cost_entries_observed_at"), "cost_entries", ["observed_at"], unique=False)

    op.create_table(
        "dependency_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=24), nullable=False),
        sa.Column("source_key", sa.String(length=200), nullable=False),
        sa.Column("target_type", sa.String(length=24), nullable=False),
        sa.Column("target_key", sa.String(length=200), nullable=False),
        sa.Column("criticality", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="healthy"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint("criticality BETWEEN 1 AND 5", name=op.f("ck_dependency_edges_dependency_criticality_range")),
        sa.CheckConstraint(
            "source_type IN ('project','service','data','api','agent','skill','model','infrastructure')",
            name=op.f("ck_dependency_edges_dependency_source_type_valid"),
        ),
        sa.CheckConstraint(
            "target_type IN ('project','service','data','api','agent','skill','model','infrastructure')",
            name=op.f("ck_dependency_edges_dependency_target_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('healthy','degraded','blocked','offline')",
            name=op.f("ck_dependency_edges_dependency_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dependency_edges")),
        sa.UniqueConstraint("source_type", "source_key", "target_type", "target_key", name="uq_dependency_edge"),
    )
    for column in ("source_type", "source_key", "target_type", "target_key", "status"):
        op.create_index(op.f(f"ix_dependency_edges_{column}"), "dependency_edges", [column], unique=False)

    op.create_table(
        "holding_alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("level", sa.String(length=24), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("dedupe_key", sa.String(length=220), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("occurrences", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "level IN ('info','watch','action_required','critical')", name=op.f("ck_holding_alerts_alert_level_valid")
        ),
        sa.CheckConstraint("status IN ('active','resolved')", name=op.f("ck_holding_alerts_alert_status_valid")),
        sa.CheckConstraint("occurrences >= 1", name=op.f("ck_holding_alerts_alert_occurrences_positive")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_holding_alerts_project_id_projects"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_holding_alerts")),
        sa.UniqueConstraint("dedupe_key", name="uq_alert_dedupe_key"),
    )
    op.create_index(op.f("ix_holding_alerts_project_id"), "holding_alerts", ["project_id"], unique=False)
    op.create_index(op.f("ix_holding_alerts_level"), "holding_alerts", ["level"], unique=False)
    op.create_index(op.f("ix_holding_alerts_source"), "holding_alerts", ["source"], unique=False)
    op.create_index(op.f("ix_holding_alerts_status"), "holding_alerts", ["status"], unique=False)

    op.create_table(
        "integration_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_key", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="unconfigured"),
        sa.Column("endpoint", sa.String(length=500), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_sla_seconds", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('healthy','degraded','blocked','offline','unconfigured')",
            name=op.f("ck_integration_states_integration_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_integration_states")),
        sa.UniqueConstraint("service_key", name="uq_integration_service_key"),
    )
    op.create_index(op.f("ix_integration_states_service_key"), "integration_states", ["service_key"], unique=False)
    op.create_index(op.f("ix_integration_states_kind"), "integration_states", ["kind"], unique=False)
    op.create_index(op.f("ix_integration_states_status"), "integration_states", ["status"], unique=False)

    op.create_table(
        "venture_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=220), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False, server_default="idea"),
        sa.Column("automation_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_economics", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("risk_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("validation_cost_micros", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decision", sa.String(length=20), nullable=False, server_default="research"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        *_timestamps(),
        sa.CheckConstraint("automation_pct BETWEEN 0 AND 100", name=op.f("ck_venture_evaluations_venture_automation_range")),
        sa.CheckConstraint("validation_cost_micros >= 0", name=op.f("ck_venture_evaluations_venture_validation_cost_nonnegative")),
        sa.CheckConstraint("decision IN ('research','build','hold','reject')", name=op.f("ck_venture_evaluations_venture_decision_valid")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_venture_evaluations")),
        sa.UniqueConstraint("key", name="uq_venture_key"),
    )
    op.create_index(op.f("ix_venture_evaluations_key"), "venture_evaluations", ["key"], unique=False)
    op.create_index(op.f("ix_venture_evaluations_decision"), "venture_evaluations", ["decision"], unique=False)


def downgrade() -> None:
    op.drop_table("venture_evaluations")
    op.drop_table("integration_states")
    op.drop_table("holding_alerts")
    op.drop_table("dependency_edges")
    op.drop_table("cost_entries")
    op.drop_table("risk_registry")
    op.drop_table("project_health_snapshots")
    op.drop_table("collector_registry")
    op.drop_table("project_operational_profiles")
