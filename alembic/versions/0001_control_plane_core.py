"""holding control plane core

Revision ID: 0001_control_plane_core
Revises:
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_control_plane_core"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PROJECT_STATUS = postgresql.ENUM(
    "active", "paused", "incubating", "archived", name="projectstatus", create_type=False
)
WORK_STATUS = postgresql.ENUM(
    "planned",
    "ready",
    "running",
    "blocked",
    "review",
    "done",
    "cancelled",
    name="workstatus",
    create_type=False,
)
CRITERION_STATUS = postgresql.ENUM(
    "pending", "verified", "rejected", name="criterionstatus", create_type=False
)
DECISION_STATUS = postgresql.ENUM(
    "pending", "approved", "rejected", "superseded", name="decisionstatus", create_type=False
)
INCIDENT_STATUS = postgresql.ENUM(
    "open", "investigating", "mitigated", "resolved", name="incidentstatus", create_type=False
)
RUN_STATUS = postgresql.ENUM(
    "queued", "running", "succeeded", "failed", "cancelled", name="runstatus", create_type=False
)
AGENT_STATUS = postgresql.ENUM(
    "active", "disabled", "degraded", name="agentstatus", create_type=False
)
RISK_LEVEL = postgresql.ENUM(
    "low", "medium", "high", "critical", name="risklevel", create_type=False
)
SEVERITY = postgresql.ENUM("sev1", "sev2", "sev3", "sev4", name="severity", create_type=False)
ENUMS = (
    PROJECT_STATUS,
    WORK_STATUS,
    CRITERION_STATUS,
    DECISION_STATUS,
    INCIDENT_STATUS,
    RUN_STATUS,
    AGENT_STATUS,
    RISK_LEVEL,
    SEVERITY,
)


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ENUMS:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=160), nullable=False),
        sa.Column("status", AGENT_STATUS, nullable=False),
        sa.Column("max_autonomy", sa.Integer(), nullable=False),
        sa.Column("model_policy", sa.JSON(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("max_autonomy BETWEEN 0 AND 6", name="autonomy_range"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_key", "agents", ["key"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", PROJECT_STATUS, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("autonomy_level", sa.Integer(), nullable=False),
        sa.Column("parent_project_id", sa.Uuid(), nullable=True),
        sa.Column("owner_agent_id", sa.Uuid(), nullable=True),
        sa.Column("repository", sa.String(length=240), nullable=True),
        sa.Column("repository_path", sa.String(length=240), nullable=True),
        sa.Column("business_unit", sa.String(length=120), nullable=True),
        sa.Column("strategic_goal", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("priority BETWEEN 0 AND 5", name="priority_range"),
        sa.CheckConstraint("autonomy_level BETWEEN 0 AND 6", name="autonomy_range"),
        sa.CheckConstraint(
            "parent_project_id IS NULL OR parent_project_id <> id",
            name="no_self_parent",
        ),
        sa.ForeignKeyConstraint(["owner_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_projects_name"),
    )
    op.create_index("ix_projects_key", "projects", ["key"], unique=True)
    op.create_index("ix_projects_parent_project_id", "projects", ["parent_project_id"])

    op.create_table(
        "milestones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("status", WORK_STATUS, nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        *timestamps(),
        sa.CheckConstraint("weight BETWEEN 1 AND 100", name="weight_range"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "key", name="uq_milestone_project_key"),
    )
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])

    op.create_table(
        "acceptance_criteria",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("status", CRITERION_STATUS, nullable=False),
        sa.Column("verifier", sa.String(length=160), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("weight BETWEEN 1 AND 100", name="weight_range"),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("milestone_id", "key", name="uq_criterion_milestone_key"),
    )
    op.create_index("ix_acceptance_criteria_milestone_id", "acceptance_criteria", ["milestone_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("milestone_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", WORK_STATUS, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("assigned_agent_id", sa.Uuid(), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("priority BETWEEN 0 AND 5", name="priority_range"),
        sa.ForeignKeyConstraint(["assigned_agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_task_idempotency_key"),
        sa.UniqueConstraint("project_id", "key", name="uq_task_project_key"),
    )
    op.create_index("ix_tasks_assigned_agent_id", "tasks", ["assigned_agent_id"])
    op.create_index("ix_tasks_milestone_id", "tasks", ["milestone_id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])

    op.create_table(
        "task_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("depends_on_task_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["depends_on_task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),
    )
    op.create_index(
        "ix_task_dependencies_depends_on_task_id", "task_dependencies", ["depends_on_task_id"]
    )
    op.create_index("ix_task_dependencies_task_id", "task_dependencies", ["task_id"])

    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=True),
        sa.Column("status", RUN_STATUS, nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("external_run_id", sa.String(length=200), nullable=True),
        sa.Column("input_metadata", sa.JSON(), nullable=False),
        sa.Column("output_metadata", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.CheckConstraint("attempt >= 1", name="attempt_positive"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_run_id", name="uq_run_external_run_id"),
    )
    op.create_index("ix_runs_agent_id", "runs", ["agent_id"])
    op.create_index("ix_runs_task_id", "runs", ["task_id"])

    op.create_table(
        "decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("risk_level", RISK_LEVEL, nullable=False),
        sa.Column("status", DECISION_STATUS, nullable=False),
        sa.Column("requires_human", sa.Boolean(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("resolution", sa.JSON(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "key", name="uq_decision_project_key"),
    )
    op.create_index("ix_decisions_project_id", "decisions", ["project_id"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=False),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("outcome", DECISION_STATUS, nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approvals_actor", "approvals", ["actor"])
    op.create_index("ix_approvals_decision_id", "approvals", ["decision_id"])

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("severity", SEVERITY, nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("status", INCIDENT_STATUS, nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("resolution", sa.JSON(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *timestamps(),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incidents_project_id", "incidents", ["project_id"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=80), nullable=True),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_actor", "audit_events", ["actor"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("incidents")
    op.drop_table("approvals")
    op.drop_table("decisions")
    op.drop_table("runs")
    op.drop_table("task_dependencies")
    op.drop_table("tasks")
    op.drop_table("acceptance_criteria")
    op.drop_table("milestones")
    op.drop_table("projects")
    op.drop_table("agents")

    bind = op.get_bind()
    for enum_type in reversed(ENUMS):
        enum_type.drop(bind, checkfirst=True)
