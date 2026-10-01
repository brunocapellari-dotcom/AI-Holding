"""seed canonical tool decisions

Revision ID: 0013_seed_tool_decisions
Revises: 0012_seed_external_integrations
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013_seed_tool_decisions"
down_revision: str | None = "0012_seed_external_integrations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TOOL_DECISIONS = (
    {
        "id": uuid.UUID("63ee461d-717c-499f-86d6-87b4ac449d01"),
        "key": "CLOUD_SQL_OPERATIONAL_DB",
        "tool_name": "Google Cloud SQL for PostgreSQL",
        "capability": "operational-database",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": "Managed PostgreSQL with regional HA, PITR and private networking.",
        "maintenance_cost": "Managed database cost without operating a database cluster.",
        "license": "managed-service",
        "risk": "Cloud dependency; retain PostgreSQL portability and tested backup/restore.",
        "rationale": "Already provisioned and aligned with the Holding operational truth model.",
        "evidence": ["infra/terraform/main.tf"],
    },
    {
        "id": uuid.UUID("17127b1a-aeba-45d0-aa9d-11c164647daf"),
        "key": "OPENTELEMETRY_STANDARD",
        "tool_name": "OpenTelemetry",
        "capability": "observability",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": "Vendor-neutral traces, metrics and log correlation.",
        "maintenance_cost": "SDK plus exporter configuration; collector only when required.",
        "license": "Apache-2.0",
        "risk": "Telemetry volume and exporter cost must be bounded.",
        "rationale": "Unifies telemetry without creating a vendor-specific observability agent layer.",
        "evidence": ["app/observability.py", "github:open-telemetry/opentelemetry-python"],
    },
    {
        "id": uuid.UUID("8ea75e9b-08c0-43ff-9162-f71bc7ff914d"),
        "key": "GITLEAKS_SECRET_SCANNING",
        "tool_name": "Gitleaks",
        "capability": "secret-scanning",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": "Dedicated source and history secret detection.",
        "maintenance_cost": "One bounded CI gate.",
        "license": "MIT",
        "risk": "False positives require explicit reviewed allowlisting, never silent suppression.",
        "rationale": "Fills secret scanning without duplicating SAST or vulnerability scanning.",
        "evidence": [".github/workflows/ci.yml", "github:gitleaks/gitleaks"],
    },
    {
        "id": uuid.UUID("82abe2b8-9af0-45fc-ad6e-b08166e2ef42"),
        "key": "SEMGREP_APPLICATION_SAST",
        "tool_name": "Semgrep",
        "capability": "application-sast",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": "Deterministic source-pattern security checks for the Holding attack surface.",
        "maintenance_cost": "Local rules plus CLI execution in the full gate.",
        "license": "LGPL-2.1-or-later/core; rules reviewed separately",
        "risk": "Rules must remain bounded to avoid noisy duplicate scanning.",
        "rationale": "Complements Bandit with Holding-specific forbidden patterns.",
        "evidence": [".semgrep.yml", "github:semgrep/semgrep"],
    },
    {
        "id": uuid.UUID("0dcc551a-1284-428f-b400-cc17643b4d0e"),
        "key": "ZIZMOR_ACTIONS_SECURITY",
        "tool_name": "zizmor",
        "capability": "github-actions-security",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": "Finds workflow-specific template, permission and credential risks.",
        "maintenance_cost": "One static workflow audit in the canonical gate.",
        "license": "MIT",
        "risk": "Workflow changes may surface findings that must fail closed until reviewed.",
        "rationale": "Covers GitHub Actions semantics not covered by Semgrep, Gitleaks or Trivy.",
        "evidence": ["scripts/full_project_gate.sh", "github:zizmorcore/zizmor"],
    },
    {
        "id": uuid.UUID("5c240038-ae90-42bf-99ee-cd216a28523c"),
        "key": "TEMPORAL_DURABLE_EXECUTION",
        "tool_name": "Temporal",
        "capability": "durable-workflows",
        "classification": "benchmark",
        "replaces_key": None,
        "benefit": "Durable workflow state and retry semantics if current execution ledger is insufficient.",
        "maintenance_cost": "Additional runtime/control plane unless it replaces existing orchestration.",
        "license": "MIT",
        "risk": "High duplication risk if installed beside the current worker/scheduler stack.",
        "rationale": "Benchmark only; adoption requires a replacement ADR and full migration/rollback proof.",
        "evidence": ["github:temporalio/temporal"],
    },
    {
        "id": uuid.UUID("db856ec8-053c-4fd6-ab55-1e0ba1fd22cb"),
        "key": "OPENFGA_FINE_GRAINED_AUTH",
        "tool_name": "OpenFGA",
        "capability": "fine-grained-authorization",
        "classification": "benchmark",
        "replaces_key": None,
        "benefit": "Relationship-based authorization if the current deterministic policy layer hits a proven gap.",
        "maintenance_cost": "New policy data model and availability dependency.",
        "license": "Apache-2.0",
        "risk": "Can create a second authorization truth if adopted additively.",
        "rationale": "Benchmark against existing identity/policy controls before any replacement.",
        "evidence": ["github:openfga/openfga"],
    },
    {
        "id": uuid.UUID("f5f0fe19-8489-45bf-b7f6-8bb70e065180"),
        "key": "ALLOYDB_SCALE_OPTION",
        "tool_name": "Google AlloyDB",
        "capability": "operational-database-scale",
        "classification": "reserve",
        "replaces_key": None,
        "benefit": "Potential higher PostgreSQL-compatible performance when measured demand requires it.",
        "maintenance_cost": "Higher service cost and migration complexity.",
        "license": "managed-service",
        "risk": "Premature migration would add cost without evidence.",
        "rationale": "Reserve until Cloud SQL metrics demonstrate a real bottleneck and positive economics.",
        "evidence": ["docs/architecture/HOLDING_FINAL_STACK_REVIEW_2026-09-15.md"],
    },
    {
        "id": uuid.UUID("fb43e22d-014d-4e23-abfc-8be1fc6f014f"),
        "key": "GOOGLE_PROVIDER_V8",
        "tool_name": "HashiCorp Google Terraform Provider v8",
        "capability": "google-cloud-infrastructure",
        "classification": "benchmark",
        "replaces_key": None,
        "benefit": "New provider generation and features.",
        "maintenance_cost": "Two-major-version migration from the current ~>6.0 constraint.",
        "license": "MPL-2.0/provider terms",
        "risk": "Unvalidated breaking changes across production infrastructure.",
        "rationale": "Do not jump majors until plan, migration, rollback and full-project gates execute.",
        "evidence": ["infra/terraform/main.tf", "github:hashicorp/terraform-provider-google"],
    },
    {
        "id": uuid.UUID("c7e141b9-df82-419e-b819-fb041c0ed88c"),
        "key": "SECOND_SECRETS_CONTROL_PLANE",
        "tool_name": "Second secrets manager",
        "capability": "secrets-management",
        "classification": "reject",
        "replaces_key": None,
        "benefit": "None demonstrated for the current Google Cloud target.",
        "maintenance_cost": "Duplicate secrets control plane and operational burden.",
        "license": "varies",
        "risk": "Split source of truth and additional credential surface.",
        "rationale": "Google Secret Manager already satisfies the current production architecture.",
        "evidence": ["infra/terraform/main.tf"],
    },
    {
        "id": uuid.UUID("6b9ca9a9-1b8a-46db-bf79-6123056464de"),
        "key": "SEPARATE_DEPENDENCY_GRAPH_DB",
        "tool_name": "Dedicated graph database",
        "capability": "dependency-graph",
        "classification": "reject",
        "replaces_key": None,
        "benefit": "No measured requirement beyond PostgreSQL typed edges today.",
        "maintenance_cost": "New database, backups, security, operations and synchronization.",
        "license": "varies",
        "risk": "Duplicate operational truth and consistency burden.",
        "rationale": "Use PostgreSQL dependency edges first; revisit only with measured query limitations.",
        "evidence": ["app/models/holding.py"],
    },
)


def upgrade() -> None:
    table = sa.table(
        "tool_decisions",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("tool_name", sa.String()),
        sa.column("capability", sa.String()),
        sa.column("classification", sa.String()),
        sa.column("replaces_key", sa.String()),
        sa.column("benefit", sa.Text()),
        sa.column("maintenance_cost", sa.Text()),
        sa.column("license", sa.String()),
        sa.column("risk", sa.Text()),
        sa.column("rationale", sa.Text()),
        sa.column("evidence", sa.JSON()),
    )
    op.bulk_insert(table, list(TOOL_DECISIONS))


def downgrade() -> None:
    keys = tuple(item["key"] for item in TOOL_DECISIONS)
    op.execute(
        sa.text("DELETE FROM tool_decisions WHERE key IN :keys").bindparams(
            sa.bindparam("keys", value=keys, expanding=True)
        )
    )
