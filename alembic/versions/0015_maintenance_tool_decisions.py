"""seed maintenance and testing tool decisions

Revision ID: 0015_maintenance_tool_decisions
Revises: 0014_capability_autonomy
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015_maintenance_tool_decisions"
down_revision: str | None = "0014_capability_autonomy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TOOL_DECISIONS = (
    {
        "id": uuid.UUID("3a2d22d5-87bc-41b2-b805-e3279406df61"),
        "key": "DEPENDABOT_NATIVE_MAINTENANCE",
        "tool_name": "GitHub Dependabot",
        "capability": "dependency-maintenance",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": "Native bounded update PRs for Python, Actions, Terraform and Docker without another runtime.",
        "maintenance_cost": "Review and full-project validation of generated pull requests.",
        "license": "github-managed-service",
        "risk": "Automated updates must never bypass the canonical full-project gate or human review for major changes.",
        "rationale": "Lowest-sprawl way to keep the stack current; no separate bot service or scheduler is required.",
        "evidence": [".github/dependabot.yml"],
    },
    {
        "id": uuid.UUID("de6d94bd-194b-47f9-b16a-36332f75015e"),
        "key": "UV_PYTHON_PACKAGE_MANAGER",
        "tool_name": "uv",
        "capability": "python-environment-and-locking",
        "classification": "benchmark",
        "replaces_key": None,
        "benefit": "Potentially faster deterministic dependency resolution and installation for CI and development.",
        "maintenance_cost": "Would introduce uv.lock and require migration of install/cache conventions.",
        "license": "Apache-2.0 OR MIT",
        "risk": "Premature adoption without a validated lockfile could create two dependency truths beside pyproject/pip.",
        "rationale": "Benchmark after runners are available; adopt only if it replaces the current install path and passes the entire gate.",
        "evidence": ["github:astral-sh/uv@0.12.15"],
    },
    {
        "id": uuid.UUID("bc98078d-742b-4da2-8860-ad57f50dba7e"),
        "key": "SCHEMATHESIS_OPENAPI_TESTING",
        "tool_name": "Schemathesis",
        "capability": "openapi-property-testing",
        "classification": "benchmark",
        "replaces_key": None,
        "benefit": "Generative OpenAPI testing can detect undocumented responses and contract edge cases beyond hand-written tests.",
        "maintenance_cost": "Generated cases need bounded configuration to avoid false positives on stateful endpoints.",
        "license": "MIT",
        "risk": "Unbounded stateful generation could create noisy failures and duplicate existing E2E coverage.",
        "rationale": "Validated as FastAPI/ASGI compatible; benchmark against the current API suite before making it mandatory.",
        "evidence": ["github:schemathesis/schemathesis@v4.27.2"],
    },
    {
        "id": uuid.UUID("4ef304c8-f00c-439d-9c2c-18aa49a691f3"),
        "key": "TRIVY_IAC_MISCONFIGURATION",
        "tool_name": "Trivy",
        "capability": "iac-misconfiguration-scanning",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": "Extends the already adopted Trivy gate to Terraform misconfiguration without adding another scanner.",
        "maintenance_cost": "One additional bounded scan in the existing quality job.",
        "license": "Apache-2.0",
        "risk": "Findings require reviewed exceptions rather than silent suppression.",
        "rationale": "Fills IaC security coverage using an existing tool, minimizing redundancy.",
        "evidence": [".github/workflows/ci.yml", "github:aquasecurity/trivy-action@v0.36.0"],
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
