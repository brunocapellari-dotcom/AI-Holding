"""add corporate registry standards

Revision ID: 0019_corporate_registries
Revises: 0018_audit_immutability
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_corporate_registries"
down_revision: str | None = "0018_audit_immutability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def _json_object(name: str) -> sa.Column:
    return sa.Column(name, sa.JSON(), nullable=False, server_default=sa.text("'{}'"))


def _json_list(name: str) -> sa.Column:
    return sa.Column(name, sa.JSON(), nullable=False, server_default=sa.text("'[]'"))


def upgrade() -> None:
    op.create_table(
        "registry_directory",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("registry_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("owner_system", sa.String(length=120), nullable=False),
        sa.Column("source_of_truth", sa.String(length=240), nullable=False),
        sa.Column("schema_version", sa.String(length=40), nullable=False, server_default="1.0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        _json_object("policy_json"),
        _json_object("compatibility_json"),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active','transitional','candidate','deprecated')",
            name=op.f("ck_registry_directory_registry_directory_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_registry_directory")),
        sa.UniqueConstraint("registry_key", name="uq_registry_directory_key"),
    )
    for column in ("registry_key", "owner_system", "status"):
        op.create_index(op.f(f"ix_registry_directory_{column}"), "registry_directory", [column])

    op.create_table(
        "tool_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("capability", sa.String(length=160), nullable=False),
        sa.Column("owner_system", sa.String(length=120), nullable=False, server_default="holding"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="candidate"),
        sa.Column("version_policy", sa.String(length=120), nullable=False, server_default="renovate"),
        sa.Column("license_spdx", sa.String(length=120), nullable=True),
        sa.Column("repository", sa.String(length=240), nullable=True),
        sa.Column("runtime_scope", sa.String(length=120), nullable=False, server_default="shared"),
        sa.Column("security_class", sa.String(length=40), nullable=False, server_default="internal"),
        _json_list("capabilities"),
        _json_list("constraints"),
        _json_list("evidence"),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('approved','candidate','restricted','deprecated','rejected')",
            name=op.f("ck_tool_registry_tool_registry_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_registry")),
        sa.UniqueConstraint("key", name="uq_tool_registry_key"),
    )
    for column in ("key", "name", "capability", "status", "license_spdx"):
        op.create_index(op.f(f"ix_tool_registry_{column}"), "tool_registry", [column])

    op.create_table(
        "source_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("owner_system", sa.String(length=120), nullable=False, server_default="research-ai"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="candidate"),
        sa.Column("authority", sa.String(length=24), nullable=False, server_default="reference"),
        sa.Column("endpoint", sa.String(length=500), nullable=True),
        sa.Column("license_spdx", sa.String(length=120), nullable=True),
        sa.Column("data_classification", sa.String(length=40), nullable=False, server_default="public"),
        sa.Column("freshness_sla_seconds", sa.Integer(), nullable=True),
        _json_object("provenance_requirements"),
        sa.Column("terms_review_status", sa.String(length=40), nullable=False, server_default="pending"),
        _json_list("evidence"),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('approved','candidate','restricted','deprecated','rejected')",
            name=op.f("ck_source_registry_source_registry_status_valid"),
        ),
        sa.CheckConstraint(
            "authority IN ('primary','secondary','reference','experimental')",
            name=op.f("ck_source_registry_source_registry_authority_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_registry")),
        sa.UniqueConstraint("key", name="uq_source_registry_key"),
    )
    for column in ("key", "source_type", "status", "authority"):
        op.create_index(op.f(f"ix_source_registry_{column}"), "source_registry", [column])

    op.create_table(
        "license_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("spdx_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("usage_policy", sa.String(length=24), nullable=False),
        _json_list("conditions"),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("reviewed_by", sa.String(length=160), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "classification IN ('permissive','weak_copyleft','strong_copyleft','source_available','proprietary','public_domain','unknown')",
            name=op.f("ck_license_registry_license_registry_classification_valid"),
        ),
        sa.CheckConstraint(
            "usage_policy IN ('approved','conditional','restricted','rejected')",
            name=op.f("ck_license_registry_license_registry_usage_policy_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_license_registry")),
        sa.UniqueConstraint("spdx_id", name="uq_license_registry_spdx"),
    )
    for column in ("spdx_id", "classification", "usage_policy"):
        op.create_index(op.f(f"ix_license_registry_{column}"), "license_registry", [column])

    op.create_table(
        "model_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("model_id", sa.String(length=200), nullable=False),
        sa.Column("owner_system", sa.String(length=120), nullable=False, server_default="hermes"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="candidate"),
        _json_list("intended_uses"),
        _json_list("prohibited_uses"),
        _json_object("data_policy"),
        _json_object("cost_policy"),
        _json_object("evaluation_gate"),
        _json_list("evidence"),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('approved','candidate','restricted','deprecated','rejected')",
            name=op.f("ck_model_registry_model_registry_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_registry")),
        sa.UniqueConstraint("key", name="uq_model_registry_key"),
    )
    for column in ("key", "provider", "status"):
        op.create_index(op.f(f"ix_model_registry_{column}"), "model_registry", [column])

    op.create_table(
        "evaluation_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("evaluation_type", sa.String(length=32), nullable=False),
        sa.Column("owner_system", sa.String(length=120), nullable=False, server_default="holding"),
        sa.Column("tool_key", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="active"),
        sa.Column("dataset_ref", sa.String(length=500), nullable=True),
        _json_object("gate_policy"),
        _json_object("latest_result"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        _json_list("evidence"),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "evaluation_type IN ('regression','benchmark','red_team','quality','safety','data_quality','security')",
            name=op.f("ck_evaluation_registry_evaluation_registry_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('active','candidate','paused','deprecated')",
            name=op.f("ck_evaluation_registry_evaluation_registry_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_evaluation_registry_project_id_projects"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluation_registry")),
        sa.UniqueConstraint("key", name="uq_evaluation_registry_key"),
    )
    for column in ("key", "project_id", "evaluation_type", "status"):
        op.create_index(op.f(f"ix_evaluation_registry_{column}"), "evaluation_registry", [column])

    op.create_table(
        "architecture_decision_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("owner_system", sa.String(length=120), nullable=False, server_default="holding"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="proposed"),
        sa.Column("document_ref", sa.String(length=500), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        _json_list("alternatives"),
        _json_list("consequences"),
        sa.Column("supersedes_key", sa.String(length=120), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        _json_list("evidence"),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('proposed','accepted','superseded','rejected','deprecated')",
            name=op.f("ck_architecture_decision_registry_architecture_decision_registry_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_architecture_decision_registry")),
        sa.UniqueConstraint("key", name="uq_architecture_decision_registry_key"),
    )
    for column in ("key", "status"):
        op.create_index(
            op.f(f"ix_architecture_decision_registry_{column}"),
            "architecture_decision_registry",
            [column],
        )

    op.create_table(
        "data_contract_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("dataset_key", sa.String(length=200), nullable=False),
        sa.Column("owner_system", sa.String(length=120), nullable=False, server_default="holding"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="candidate"),
        sa.Column(
            "contract_format",
            sa.String(length=80),
            nullable=False,
            server_default="holding-data-contract-v1",
        ),
        sa.Column("engine", sa.String(length=80), nullable=False, server_default="native"),
        sa.Column("contract_ref", sa.String(length=500), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        _json_list("required_checks"),
        _json_object("latest_result"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()),
        _json_list("evidence"),
        _json_object("metadata_json"),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active','candidate','deprecated','failed')",
            name=op.f("ck_data_contract_registry_data_contract_registry_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_data_contract_registry_project_id_projects"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_contract_registry")),
        sa.UniqueConstraint("key", name="uq_data_contract_registry_key"),
    )
    for column in ("key", "project_id", "dataset_key", "status"):
        op.create_index(
            op.f(f"ix_data_contract_registry_{column}"),
            "data_contract_registry",
            [column],
        )


def downgrade() -> None:
    op.drop_table("data_contract_registry")
    op.drop_table("architecture_decision_registry")
    op.drop_table("evaluation_registry")
    op.drop_table("model_registry")
    op.drop_table("license_registry")
    op.drop_table("source_registry")
    op.drop_table("tool_registry")
    op.drop_table("registry_directory")
