"""seed corporate registry policy baseline

Revision ID: 0020_corporate_registry_baseline
Revises: 0019_corporate_registries
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0020_corporate_registry_baseline"
down_revision: str | None = "0019_corporate_registries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id(key: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"https://ai-holding.local/registry/{key}")


REGISTRIES = (
    ("tool", "Tool Registry", "holding", "holding-control-plane:tool_registry"),
    ("source", "Source Registry", "holding", "holding-control-plane:source_registry"),
    ("license", "License Registry", "holding", "holding-control-plane:license_registry"),
    ("model", "Model Registry", "hermes", "holding-control-plane:model_registry"),
    (
        "evaluation",
        "Evaluation Registry",
        "holding-auditor",
        "holding-control-plane:evaluation_registry",
    ),
    ("risk", "Risk Registry", "holding", "holding-control-plane:risk_registry"),
    ("cost", "Cost Registry", "holding-finops", "holding-control-plane:cost_entries"),
    (
        "architecture-decision",
        "Architecture Decision Registry",
        "holding-architecture",
        "git:docs/architecture",
    ),
    (
        "data-contract",
        "Data Contract Registry",
        "holding-data-governance",
        "git:data-contracts + holding-control-plane:data_contract_registry",
    ),
    (
        "project",
        "Project Registry",
        "holding",
        "holding-control-plane:projects+project_operational_profiles",
    ),
)

LICENSES = (
    {
        "spdx_id": "MIT",
        "name": "MIT License",
        "classification": "permissive",
        "usage_policy": "approved",
        "conditions": ["retain copyright and license notice"],
        "source_url": "https://spdx.org/licenses/MIT.html",
    },
    {
        "spdx_id": "Apache-2.0",
        "name": "Apache License 2.0",
        "classification": "permissive",
        "usage_policy": "approved",
        "conditions": ["retain license/NOTICE obligations where applicable"],
        "source_url": "https://spdx.org/licenses/Apache-2.0.html",
    },
    {
        "spdx_id": "Apache-2.0 OR MIT",
        "name": "Apache-2.0 OR MIT",
        "classification": "permissive",
        "usage_policy": "approved",
        "conditions": ["preserve chosen license obligations when redistributing"],
        "source_url": "https://spdx.org/licenses/",
    },
    {
        "spdx_id": "AGPL-3.0-only",
        "name": "GNU Affero General Public License v3.0 only",
        "classification": "strong_copyleft",
        "usage_policy": "conditional",
        "conditions": [
            "no embedding into proprietary product without legal review",
            "network-service source obligations require explicit review",
        ],
        "source_url": "https://spdx.org/licenses/AGPL-3.0-only.html",
    },
    {
        "spdx_id": "Elastic-2.0",
        "name": "Elastic License 2.0",
        "classification": "source_available",
        "usage_policy": "conditional",
        "conditions": [
            "internal/self-hosted use only unless separately reviewed",
            "do not offer substantial licensed functionality as a hosted managed service",
        ],
        "source_url": "https://www.elastic.co/licensing/elastic-license",
    },
    {
        "spdx_id": "LicenseRef-Managed-Service",
        "name": "Managed service terms",
        "classification": "proprietary",
        "usage_policy": "conditional",
        "conditions": ["provider terms, data policy and commercial terms require review"],
        "source_url": None,
    },
)

TOOLS = (
    {
        "key": "MISE_CORPORATE_TOOLCHAIN",
        "name": "mise",
        "capability": "toolchain-versioning-and-tasks",
        "status": "approved",
        "license_spdx": "MIT",
        "repository": "jdx/mise",
        "runtime_scope": "development-ci",
        "capabilities": ["tool versions", "environment", "task runner", "lockfile"],
        "constraints": ["one root mise.toml per repository", "no duplicate version manager"],
    },
    {
        "key": "UV_CORPORATE_PYTHON",
        "name": "uv",
        "capability": "python-environment-and-locking",
        "status": "approved",
        "license_spdx": "Apache-2.0 OR MIT",
        "repository": "astral-sh/uv",
        "runtime_scope": "development-ci-build",
        "capabilities": ["uv.lock", "exact sync", "workspaces", "SBOM export"],
        "constraints": [
            "uv.lock is canonical Python resolution",
            "do not maintain parallel pip lock truth",
        ],
    },
    {
        "key": "RUFF_CORPORATE_LINT",
        "name": "Ruff",
        "capability": "python-lint-format",
        "status": "approved",
        "license_spdx": "MIT",
        "repository": "astral-sh/ruff",
        "runtime_scope": "development-ci",
        "capabilities": ["lint", "format"],
        "constraints": ["projects may extend rules but not replace Ruff without ADR"],
    },
    {
        "key": "PRE_COMMIT_LOCAL_GATE",
        "name": "pre-commit",
        "capability": "developer-local-quality-gate",
        "status": "approved",
        "license_spdx": "MIT",
        "repository": "pre-commit/pre-commit",
        "runtime_scope": "development",
        "capabilities": ["local hooks"],
        "constraints": ["hooks call canonical project tools; no duplicate lint implementation"],
    },
    {
        "key": "RENOVATE_CORPORATE_DEPENDENCIES",
        "name": "Renovate",
        "capability": "dependency-maintenance",
        "status": "approved",
        "license_spdx": "AGPL-3.0-only",
        "repository": "renovatebot/renovate",
        "runtime_scope": "hosted-github-app",
        "capabilities": [
            "dependency cooldown",
            "uv lock maintenance",
            "Actions",
            "Terraform",
            "Docker",
        ],
        "constraints": [
            "use hosted GitHub App rather than embedding Renovate into product runtime",
            "minimumReleaseAge enforced",
            "major upgrades require Dependency Dashboard approval and human review",
        ],
    },
    {
        "key": "DEPENDABOT_TRANSITIONAL",
        "name": "GitHub Dependabot",
        "capability": "dependency-maintenance",
        "status": "deprecated",
        "license_spdx": "LicenseRef-Managed-Service",
        "repository": None,
        "runtime_scope": "github",
        "capabilities": ["dependency update PRs"],
        "constraints": ["remove configuration when Renovate GitHub App is connected"],
    },
    {
        "key": "PHOENIX_AI_OBSERVABILITY",
        "name": "Arize Phoenix",
        "capability": "ai-tracing-evaluation-experiments",
        "status": "approved",
        "license_spdx": "Elastic-2.0",
        "repository": "Arize-ai/phoenix",
        "runtime_scope": "internal-observability",
        "capabilities": ["OTLP tracing", "OpenInference", "datasets", "experiments", "evaluations"],
        "constraints": ["internal/self-hosted only", "OpenTelemetry remains transport standard"],
    },
    {
        "key": "PROMPTFOO_AI_REGRESSION",
        "name": "Promptfoo",
        "capability": "ai-regression-red-team",
        "status": "approved",
        "license_spdx": "MIT",
        "repository": "promptfoo/promptfoo",
        "runtime_scope": "ci-security-test-lab",
        "capabilities": ["LLM evals", "red team", "MCP security tests", "quality gates"],
        "constraints": [
            "disable telemetry/cloud sharing by default",
            "treat configs/providers as executable code and review them",
        ],
    },
    {
        "key": "SODA_DATA_CONTRACTS",
        "name": "Soda Core",
        "capability": "data-quality-contract-engine",
        "status": "candidate",
        "license_spdx": "Elastic-2.0",
        "repository": "sodadata/soda-core",
        "runtime_scope": "data-quality",
        "capabilities": ["data quality checks", "data contract verification"],
        "constraints": [
            "benchmark only",
            "native Holding contract schema remains canonical",
            "do not make Soda-specific YAML the only portable contract representation",
        ],
    },
    {
        "key": "TOOLHIVE_MCP_GOVERNANCE",
        "name": "ToolHive",
        "capability": "mcp-registry-isolation-policy-audit",
        "status": "candidate",
        "license_spdx": "Apache-2.0",
        "repository": "stacklok/toolhive",
        "runtime_scope": "mcp-platform",
        "capabilities": [
            "registry",
            "gateway",
            "runtime isolation",
            "OIDC",
            "audit",
            "OpenTelemetry",
        ],
        "constraints": [
            "benchmark registry/gateway first",
            "must not become a second Holding or Hermes control plane",
            "prefer compatibility with official MCP Registry API",
        ],
    },
    {
        "key": "PLANE_PROJECT_CONTROL_PLANE",
        "name": "Plane",
        "capability": "project-work-management",
        "status": "candidate",
        "license_spdx": "AGPL-3.0-only",
        "repository": "makeplane/plane",
        "runtime_scope": "project-management",
        "capabilities": [
            "projects",
            "work items",
            "cycles",
            "modules",
            "webhooks",
            "REST API",
            "MCP",
        ],
        "constraints": [
            "benchmark as UI/reference only until it proves replacement value",
            "do not duplicate Holding Project/Task/PMO truth",
            "AGPL deployment requires explicit license review",
        ],
    },
)

EVALUATIONS = (
    (
        "AI_TRACE_EVAL_PHOENIX",
        "Phoenix trace evaluation",
        "quality",
        "PHOENIX_AI_OBSERVABILITY",
        {"required": True, "role": "production-trace-evaluation"},
    ),
    (
        "AI_REGRESSION_PROMPTFOO",
        "Promptfoo LLM regression gate",
        "regression",
        "PROMPTFOO_AI_REGRESSION",
        {"required": True, "fail_on_regression": True},
    ),
    (
        "AI_REDTEAM_PROMPTFOO",
        "Promptfoo AI security red-team gate",
        "red_team",
        "PROMPTFOO_AI_REGRESSION",
        {"required": True, "security_test_lab": True},
    ),
    (
        "DATA_CONTRACT_NATIVE",
        "Holding native data contract verification",
        "data_quality",
        None,
        {"required": True, "engine": "native", "soda": "benchmark-adapter"},
    ),
)

TOOL_DECISIONS = (
    (
        "MISE_CORPORATE_STANDARD",
        "mise",
        "toolchain-versioning-and-tasks",
        "adopt",
        None,
        "One tool/version/task entry point across projects.",
        "MIT",
    ),
    (
        "UV_CORPORATE_STANDARD",
        "uv",
        "python-environment-and-locking",
        "adopt",
        None,
        "Canonical Python environment and lock workflow.",
        "Apache-2.0 OR MIT",
    ),
    (
        "PRE_COMMIT_CORPORATE_STANDARD",
        "pre-commit",
        "developer-local-quality-gate",
        "adopt",
        None,
        "Runs the same canonical tools locally before CI.",
        "MIT",
    ),
    (
        "RENOVATE_REPLACES_DEPENDABOT",
        "Renovate",
        "dependency-maintenance",
        "replace",
        "DEPENDABOT_NATIVE_MAINTENANCE",
        "Adds cooldown, uv lock maintenance and explicit major-upgrade approval.",
        "AGPL-3.0-only",
    ),
    (
        "PHOENIX_CORPORATE_AI_OBSERVABILITY",
        "Arize Phoenix",
        "ai-tracing-evaluation-experiments",
        "adopt",
        None,
        "OpenTelemetry-compatible AI tracing and evaluation standard.",
        "Elastic-2.0",
    ),
    (
        "PROMPTFOO_CORPORATE_AI_GATE",
        "Promptfoo",
        "ai-regression-red-team",
        "adopt",
        None,
        "Deterministic CI evaluation and red-team gate for AI systems.",
        "MIT",
    ),
    (
        "SODA_DATA_CONTRACT_BENCHMARK",
        "Soda Core",
        "data-quality-contract-engine",
        "benchmark",
        None,
        "Evaluate as an engine behind the native corporate Data Contract schema.",
        "Elastic-2.0",
    ),
    (
        "TOOLHIVE_MCP_BENCHMARK",
        "ToolHive",
        "mcp-registry-isolation-policy-audit",
        "benchmark",
        None,
        "Evaluate Registry/Gateway compatibility without duplicating Hermes/Holding.",
        "Apache-2.0",
    ),
    (
        "PLANE_PROJECT_CONTROL_PLANE_BENCHMARK",
        "Plane",
        "project-work-management",
        "benchmark",
        None,
        "Use as replacement/reference benchmark, never parallel project truth.",
        "AGPL-3.0-only",
    ),
)


def upgrade() -> None:
    now = datetime(2026, 9, 21, tzinfo=UTC)

    directory = sa.table(
        "registry_directory",
        sa.column("id", sa.Uuid()),
        sa.column("registry_key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("owner_system", sa.String()),
        sa.column("source_of_truth", sa.String()),
        sa.column("schema_version", sa.String()),
        sa.column("status", sa.String()),
        sa.column("policy_json", sa.JSON()),
        sa.column("compatibility_json", sa.JSON()),
        sa.column("metadata_json", sa.JSON()),
    )
    op.bulk_insert(
        directory,
        [
            {
                "id": _id(f"registry:{key}"),
                "registry_key": key,
                "name": name,
                "owner_system": owner,
                "source_of_truth": source,
                "schema_version": "1.0",
                "status": "active",
                "policy_json": {
                    "mandatory_for_all_projects": True,
                    "no_parallel_source_of_truth": True,
                    "exceptions_require_adr": True,
                },
                "compatibility_json": {},
                "metadata_json": {},
            }
            for key, name, owner, source in REGISTRIES
        ],
    )

    licenses = sa.table(
        "license_registry",
        sa.column("id", sa.Uuid()),
        sa.column("spdx_id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("classification", sa.String()),
        sa.column("usage_policy", sa.String()),
        sa.column("conditions", sa.JSON()),
        sa.column("source_url", sa.String()),
        sa.column("reviewed_by", sa.String()),
        sa.column("reviewed_at", sa.DateTime(timezone=True)),
        sa.column("metadata_json", sa.JSON()),
    )
    op.bulk_insert(
        licenses,
        [
            {
                "id": _id(f"license:{item['spdx_id']}"),
                **item,
                "reviewed_by": "holding-architecture",
                "reviewed_at": now,
                "metadata_json": {},
            }
            for item in LICENSES
        ],
    )

    tools = sa.table(
        "tool_registry",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("name", sa.String()),
        sa.column("capability", sa.String()),
        sa.column("owner_system", sa.String()),
        sa.column("status", sa.String()),
        sa.column("version_policy", sa.String()),
        sa.column("license_spdx", sa.String()),
        sa.column("repository", sa.String()),
        sa.column("runtime_scope", sa.String()),
        sa.column("security_class", sa.String()),
        sa.column("capabilities", sa.JSON()),
        sa.column("constraints", sa.JSON()),
        sa.column("evidence", sa.JSON()),
        sa.column("metadata_json", sa.JSON()),
    )
    op.bulk_insert(
        tools,
        [
            {
                "id": _id(f"tool:{item['key']}"),
                **item,
                "owner_system": "holding",
                "version_policy": "renovate",
                "security_class": "internal",
                "evidence": ["docs/architecture/CORPORATE_STANDARDS_2026-09-21.md"],
                "metadata_json": {},
            }
            for item in TOOLS
        ],
    )

    evaluations = sa.table(
        "evaluation_registry",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("project_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("evaluation_type", sa.String()),
        sa.column("owner_system", sa.String()),
        sa.column("tool_key", sa.String()),
        sa.column("status", sa.String()),
        sa.column("dataset_ref", sa.String()),
        sa.column("gate_policy", sa.JSON()),
        sa.column("latest_result", sa.JSON()),
        sa.column("last_run_at", sa.DateTime(timezone=True)),
        sa.column("evidence", sa.JSON()),
        sa.column("metadata_json", sa.JSON()),
    )
    op.bulk_insert(
        evaluations,
        [
            {
                "id": _id(f"evaluation:{key}"),
                "key": key,
                "project_id": None,
                "name": name,
                "evaluation_type": evaluation_type,
                "owner_system": "holding-auditor",
                "tool_key": tool_key,
                "status": "active",
                "dataset_ref": None,
                "gate_policy": gate_policy,
                "latest_result": {},
                "last_run_at": None,
                "evidence": [],
                "metadata_json": {"corporate_default": True},
            }
            for key, name, evaluation_type, tool_key, gate_policy in EVALUATIONS
        ],
    )

    adrs = sa.table(
        "architecture_decision_registry",
        sa.column("id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("title", sa.String()),
        sa.column("owner_system", sa.String()),
        sa.column("status", sa.String()),
        sa.column("document_ref", sa.String()),
        sa.column("rationale", sa.Text()),
        sa.column("alternatives", sa.JSON()),
        sa.column("consequences", sa.JSON()),
        sa.column("supersedes_key", sa.String()),
        sa.column("decided_at", sa.DateTime(timezone=True)),
        sa.column("evidence", sa.JSON()),
        sa.column("metadata_json", sa.JSON()),
    )
    op.bulk_insert(
        adrs,
        [
            {
                "id": _id("adr:CORPORATE_STANDARDS_2026_09_21"),
                "key": "CORPORATE_STANDARDS_2026_09_21",
                "title": "Corporate registries and shared development standards",
                "owner_system": "holding-architecture",
                "status": "accepted",
                "document_ref": "docs/architecture/CORPORATE_STANDARDS_2026-09-21.md",
                "rationale": "One governed standard for transversal capabilities prevents tool and truth fragmentation.",
                "alternatives": ["independent per-project stacks", "duplicate registries"],
                "consequences": [
                    "exceptions require an ADR",
                    "projects consume shared standards instead of rebuilding them",
                ],
                "supersedes_key": None,
                "decided_at": now,
                "evidence": ["research-round-2026-09-21"],
                "metadata_json": {},
            }
        ],
    )

    decisions = sa.table(
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
    op.bulk_insert(
        decisions,
        [
            {
                "id": _id(f"tool-decision:{key}"),
                "key": key,
                "tool_name": tool_name,
                "capability": capability,
                "classification": classification,
                "replaces_key": replaces_key,
                "benefit": benefit,
                "maintenance_cost": "Governed by the corporate Tool Registry and Renovate policy.",
                "license": license_id,
                "risk": "Must pass license, security, cost, migration and no-duplication gates.",
                "rationale": benefit,
                "evidence": ["docs/architecture/CORPORATE_STANDARDS_2026-09-21.md"],
            }
            for key, tool_name, capability, classification, replaces_key, benefit, license_id in TOOL_DECISIONS
        ],
    )


def downgrade() -> None:
    for table_name, key_column, keys in (
        ("tool_decisions", "key", [item[0] for item in TOOL_DECISIONS]),
        ("architecture_decision_registry", "key", ["CORPORATE_STANDARDS_2026_09_21"]),
        ("evaluation_registry", "key", [item[0] for item in EVALUATIONS]),
        ("tool_registry", "key", [item["key"] for item in TOOLS]),
        ("license_registry", "spdx_id", [item["spdx_id"] for item in LICENSES]),
        ("registry_directory", "registry_key", [item[0] for item in REGISTRIES]),
    ):
        op.execute(
            sa.text(f"DELETE FROM {table_name} WHERE {key_column} IN :keys").bindparams(
                sa.bindparam("keys", value=tuple(keys), expanding=True)
            )
        )
