"""control plane operational registries

Revision ID: 0023_control_plane_registry
Revises: 0022_platform_review_round2
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023_control_plane_registry"
down_revision: str | None = "0022_platform_review_round2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'blocked'")
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'maintenance'")
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'discontinued'")
    op.execute("ALTER TYPE workstatus ADD VALUE IF NOT EXISTS 'testing'")

    op.create_table(
        "release_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("commercial_status", sa.String(length=24), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('PLANNED','IN_PROGRESS','BLOCKED','TESTING','REVIEW','READY','RELEASED','FAILED','ROLLED_BACK')",
            name="release_status_valid",
        ),
        sa.CheckConstraint(
            "commercial_status IN ('NOT_READY','DEMO','PILOT','SELLABLE','CUSTOMERS','SCALING')",
            name="release_commercial_status_valid",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", name="uq_release_project_name"),
    )
    op.create_index("ix_release_registry_project_id", "release_registry", ["project_id"])
    op.create_index("ix_release_registry_status", "release_registry", ["status"])
    op.create_index(
        "ix_release_registry_commercial_status", "release_registry", ["commercial_status"]
    )

    op.create_table(
        "project_governance_state",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("declared_status", sa.String(length=24), nullable=False),
        sa.Column("verified_status", sa.String(length=24), nullable=False),
        sa.Column("priority_tier", sa.String(length=2), nullable=False),
        sa.Column("current_release_id", sa.Uuid(), nullable=True),
        sa.Column("health_status", sa.String(length=20), nullable=False),
        sa.Column("cost_status", sa.String(length=20), nullable=False),
        sa.Column("commercial_status", sa.String(length=24), nullable=False),
        sa.Column("monthly_budget_micros", sa.BigInteger(), nullable=False),
        sa.Column("next_best_action", sa.Text(), nullable=True),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_activity", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stalled", sa.Boolean(), nullable=False),
        sa.Column("execution_risk", sa.Boolean(), nullable=False),
        sa.Column("scope_creep", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
        sa.CheckConstraint(
            "declared_status IN ('ACTIVE','PAUSED','BLOCKED','MAINTENANCE','ARCHIVED','DISCONTINUED','DONE','UNKNOWN')",
            name="declared_status_valid",
        ),
        sa.CheckConstraint(
            "verified_status IN ('UNKNOWN','NOT_DONE','BLOCKED','READY','RELEASED','FAILED','STALE')",
            name="verified_status_valid",
        ),
        sa.CheckConstraint("priority_tier IN ('P0','P1','P2','P3')", name="priority_tier_valid"),
        sa.CheckConstraint(
            "health_status IN ('HEALTHY','DEGRADED','UNHEALTHY','UNKNOWN')",
            name="governance_health_valid",
        ),
        sa.CheckConstraint(
            "cost_status IN ('NORMAL','WARNING','OVER_BUDGET')",
            name="governance_cost_status_valid",
        ),
        sa.CheckConstraint(
            "commercial_status IN ('NOT_READY','DEMO','PILOT','SELLABLE','CUSTOMERS','SCALING')",
            name="governance_commercial_status_valid",
        ),
        sa.CheckConstraint("monthly_budget_micros >= 0", name="monthly_budget_nonnegative"),
        sa.ForeignKeyConstraint(
            ["current_release_id"], ["release_registry.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_index(
        "ix_project_governance_state_verified_status", "project_governance_state", ["verified_status"]
    )
    op.create_index(
        "ix_project_governance_state_priority_tier", "project_governance_state", ["priority_tier"]
    )
    op.create_index(
        "ix_project_governance_state_current_release_id",
        "project_governance_state",
        ["current_release_id"],
    )
    op.create_index(
        "ix_project_governance_state_health_status", "project_governance_state", ["health_status"]
    )
    op.create_index(
        "ix_project_governance_state_cost_status", "project_governance_state", ["cost_status"]
    )
    op.create_index(
        "ix_project_governance_state_commercial_status", "project_governance_state", ["commercial_status"]
    )

    op.create_table(
        "release_gate_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=False),
        sa.Column("gate_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("evidence_required", sa.Boolean(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "gate_type IN ('CODE','TEST','SECURITY','E2E','DEPLOY','OPERATIONS','COMMERCIAL')",
            name="release_gate_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ('NOT_STARTED','IN_PROGRESS','PASS','FAIL','WAIVED')",
            name="release_gate_status_valid",
        ),
        sa.ForeignKeyConstraint(["release_id"], ["release_registry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("release_id", "gate_type", name="uq_release_gate_type"),
    )
    op.create_index("ix_release_gate_registry_release_id", "release_gate_registry", ["release_id"])
    op.create_index("ix_release_gate_registry_status", "release_gate_registry", ["status"])

    op.create_table(
        "evidence_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("release_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=28), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("artifact_reference", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(length=16), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('COMMIT','PR','CI_RUN','TEST_RESULT','SCREENSHOT','LOG','ENDPOINT_HEALTH','DEPLOYMENT','ARTIFACT','REPORT','E2E_EXECUTION')",
            name="evidence_kind_valid",
        ),
        sa.CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')",
            name="evidence_verification_status_valid",
        ),
        sa.CheckConstraint(
            "task_id IS NOT NULL OR release_id IS NOT NULL OR project_id IS NOT NULL",
            name="evidence_has_owner",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["release_registry.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "project_id",
        "task_id",
        "release_id",
        "kind",
        "verification_status",
        "observed_at",
    ):
        op.create_index(f"ix_evidence_registry_{column}", "evidence_registry", [column])

    op.create_table(
        "service_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("environment", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=120), nullable=True),
        sa.Column("endpoint", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_deploy", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dependencies", sa.JSON(), nullable=False),
        sa.Column("owner", sa.String(length=160), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('HEALTHY','DEGRADED','UNHEALTHY','UNKNOWN')",
            name="service_status_valid",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "name", "environment", name="uq_service_project_env"),
    )
    op.create_index("ix_service_registry_project_id", "service_registry", ["project_id"])
    op.create_index("ix_service_registry_environment", "service_registry", ["environment"])
    op.create_index("ix_service_registry_status", "service_registry", ["status"])

    op.create_table(
        "deployment_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=True),
        sa.Column("release_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.String(length=120), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=80), nullable=False),
        sa.Column("deployment_ref", sa.String(length=240), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rollback_target", sa.String(length=240), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING','DEPLOYING','HEALTHY','FAILED','ROLLED_BACK')",
            name="deployment_status_valid",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["service_registry.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["release_id"], ["release_registry.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deployment_ref"),
    )
    for column in ("project_id", "service_id", "release_id", "commit_sha", "environment", "status", "started_at"):
        op.create_index(f"ix_deployment_registry_{column}", "deployment_registry", [column])

    op.create_table(
        "test_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("suite", sa.String(length=180), nullable=False),
        sa.Column("test_type", sa.String(length=20), nullable=False),
        sa.Column("commit_sha", sa.String(length=64), nullable=False),
        sa.Column("environment", sa.String(length=80), nullable=False),
        sa.Column("result", sa.String(length=12), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "test_type IN ('UNIT','INTEGRATION','E2E','SECURITY','REGRESSION','SMOKE')",
            name="test_type_valid",
        ),
        sa.CheckConstraint("result IN ('PASS','FAIL','SKIPPED')", name="test_result_valid"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["release_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "project_id",
        "release_id",
        "task_id",
        "test_type",
        "commit_sha",
        "result",
        "observed_at",
    ):
        op.create_index(f"ix_test_registry_{column}", "test_registry", [column])

    op.create_table(
        "blocker_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("blocker_type", sa.String(length=28), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=160), nullable=False),
        sa.Column("action_required", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
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
        sa.CheckConstraint(
            "blocker_type IN ('CREDENTIAL','ACCESS','PAYMENT','LEGAL','TECHNICAL','EXTERNAL_DEPENDENCY','HUMAN_DECISION')",
            name="blocker_type_valid",
        ),
        sa.CheckConstraint("status IN ('OPEN','RESOLVED')", name="blocker_status_valid"),
        sa.CheckConstraint("priority IN ('P0','P1','P2','P3')", name="blocker_priority_valid"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["release_registry.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("project_id", "release_id", "task_id", "blocker_type", "priority", "status"):
        op.create_index(f"ix_blocker_registry_{column}", "blocker_registry", [column])

    op.add_column("tasks", sa.Column("release_id", sa.Uuid(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column(
            "acceptance_criteria", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False
        ),
    )
    op.add_column(
        "tasks",
        sa.Column("test_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "evidence_required", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    op.add_column("tasks", sa.Column("commit_sha", sa.String(length=64), nullable=True))
    op.add_column("tasks", sa.Column("deployment_ref", sa.String(length=240), nullable=True))
    op.create_foreign_key(
        "fk_tasks_release_id",
        "tasks",
        "release_registry",
        ["release_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_tasks_release_id", "tasks", ["release_id"])

    op.add_column(
        "dependency_edges",
        sa.Column(
            "requirement_class", sa.String(length=12), server_default="REQUIRED", nullable=False
        ),
    )
    op.add_column(
        "dependency_edges",
        sa.Column("artificial", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_check_constraint(
        "dependency_requirement_class_valid",
        "dependency_edges",
        "requirement_class IN ('REQUIRED','OPTIONAL','DEFERRED')",
    )
    op.create_index(
        "ix_dependency_edges_requirement_class", "dependency_edges", ["requirement_class"]
    )


def downgrade() -> None:
    op.drop_index("ix_dependency_edges_requirement_class", table_name="dependency_edges")
    op.drop_constraint("dependency_requirement_class_valid", "dependency_edges", type_="check")
    op.drop_column("dependency_edges", "artificial")
    op.drop_column("dependency_edges", "requirement_class")

    op.drop_index("ix_tasks_release_id", table_name="tasks")
    op.drop_constraint("fk_tasks_release_id", "tasks", type_="foreignkey")
    for column in (
        "deployment_ref",
        "commit_sha",
        "evidence_required",
        "test_required",
        "acceptance_criteria",
        "release_id",
    ):
        op.drop_column("tasks", column)

    for table in (
        "blocker_registry",
        "test_registry",
        "deployment_registry",
        "service_registry",
        "evidence_registry",
        "release_gate_registry",
        "project_governance_state",
        "release_registry",
    ):
        op.drop_table(table)
