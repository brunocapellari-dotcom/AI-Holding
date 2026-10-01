"""seed second 2026-09-28 platform review decisions

Revision ID: 0022_platform_review_round2
Revises: 0021_supply_chain_review
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022_platform_review_round2"
down_revision: str | None = "0021_supply_chain_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TOOL_DECISIONS = (
    {
        "id": uuid.UUID("0a9f5521-62bd-4e30-a463-b873aa30e251"),
        "key": "DEPENDENCY_TRACK_PORTFOLIO_SBOM",
        "tool_name": "OWASP Dependency-Track",
        "capability": "portfolio-sbom-and-vulnerability-intelligence",
        "classification": "benchmark",
        "replaces_key": None,
        "benefit": (
            "Could aggregate CycloneDX SBOMs and component risk across the whole portfolio "
            "instead of leaving build evidence as isolated files."
        ),
        "maintenance_cost": (
            "Adds a persistent security application, database, upgrades and another "
            "availability surface."
        ),
        "license": "Apache-2.0",
        "risk": (
            "Can duplicate the Holding Security Finding Registry unless ingestion ownership "
            "and source-of-truth boundaries are explicit."
        ),
        "rationale": (
            "Benchmark against a native Holding SBOM/evidence collector before adopting "
            "another permanent control plane."
        ),
        "evidence": ["github:DependencyTrack/dependency-track@5.1.1"],
    },
    {
        "id": uuid.UUID("6cf4f948-fc32-4271-8247-d4e342186a67"),
        "key": "OPENTOFU_TERRAFORM_REPLACEMENT",
        "tool_name": "OpenTofu",
        "capability": "infrastructure-as-code",
        "classification": "benchmark",
        "replaces_key": None,
        "benefit": (
            "MPL-2.0 Terraform-compatible infrastructure engine with an independent "
            "open-source governance path."
        ),
        "maintenance_cost": (
            "Replacement requires state, provider, plan and rollback equivalence testing "
            "for the complete production infrastructure."
        ),
        "license": "MPL-2.0",
        "risk": (
            "Changing IaC engine before production acceptance adds migration risk with no "
            "measured runtime benefit."
        ),
        "rationale": (
            "Evaluate only as a full Terraform replacement after the current GCP release "
            "path is proven; never operate both engines as independent state owners."
        ),
        "evidence": ["github:opentofu/opentofu@v1.12.6"],
    },
    {
        "id": uuid.UUID("afcc11f7-b5c4-4136-a187-98f069d99bc0"),
        "key": "GUAC_PARALLEL_SUPPLY_CHAIN_GRAPH",
        "tool_name": "GUAC",
        "capability": "software-supply-chain-graph",
        "classification": "reserve",
        "replaces_key": None,
        "benefit": (
            "Can aggregate SBOM, provenance and security metadata into a queryable graph "
            "if portfolio-scale supply-chain analysis later requires it."
        ),
        "maintenance_cost": "Additional graph ingestion, APIs, storage and operational ownership.",
        "license": "Apache-2.0",
        "risk": "Would overlap the Holding dependency graph and canonical evidence registries.",
        "rationale": (
            "Reserve until native relational evidence queries demonstrate a measured graph need."
        ),
        "evidence": ["github:guacsec/guac@v1.1.0"],
    },
    {
        "id": uuid.UUID("6439ee75-aede-42fe-a879-83fe4162a736"),
        "key": "OSV_SCANNER_PARALLEL_GATE",
        "tool_name": "OSV-Scanner",
        "capability": "dependency-vulnerability-and-license-scanning",
        "classification": "reserve",
        "replaces_key": None,
        "benefit": (
            "Call analysis and OSV-native remediation may help targeted investigations "
            "when Trivy or pip-audit findings are ambiguous."
        ),
        "maintenance_cost": "Another vulnerability database/client and another CI result stream.",
        "license": "Apache-2.0",
        "risk": "Adding it to every build would duplicate Trivy and pip-audit coverage.",
        "rationale": (
            "Keep as an investigation tool, not a mandatory Holding gate, unless it proves "
            "a reproducible false-positive reduction."
        ),
        "evidence": ["github:google/osv-scanner@v2.6.0"],
    },
    {
        "id": uuid.UUID("4e043c64-3ca1-42ff-a96b-67f2b6b8e3a1"),
        "key": "GRYPE_PARALLEL_VULNERABILITY_GATE",
        "tool_name": "Grype",
        "capability": "container-and-sbom-vulnerability-scanning",
        "classification": "reject",
        "replaces_key": None,
        "benefit": "No uncovered mandatory gate after Trivy plus Syft are already canonical.",
        "maintenance_cost": "Duplicates vulnerability policy, databases and exception handling.",
        "license": "Apache-2.0",
        "risk": "Conflicting vulnerability results would add triage noise without new ownership.",
        "rationale": "Retain one vulnerability gate unless a measured detection gap appears.",
        "evidence": ["github:anchore/grype@v0.119.0"],
    },
    {
        "id": uuid.UUID("e159e2f8-b882-4766-ae6d-890d37f6d084"),
        "key": "DAGGER_PARALLEL_CI_ENGINE",
        "tool_name": "Dagger",
        "capability": "portable-ci-pipeline-engine",
        "classification": "reject",
        "replaces_key": None,
        "benefit": (
            "Portable containerized pipelines are valuable, but the existing full-project "
            "gate already preserves portability outside Cloud Build."
        ),
        "maintenance_cost": "Adds another CI execution abstraction and cache/runtime layer.",
        "license": "Apache-2.0",
        "risk": "Creates a second pipeline truth beside Cloud Build and shell acceptance gates.",
        "rationale": "Do not add while Cloud Build remains the canonical executor.",
        "evidence": ["github:dagger/dagger@v0.21.9"],
    },
    {
        "id": uuid.UUID("48cf9439-7af7-4af1-bc85-adf3d20c16b7"),
        "key": "BACKSTAGE_PARALLEL_PROJECT_PORTAL",
        "tool_name": "Backstage",
        "capability": "developer-portal-and-service-catalog",
        "classification": "reject",
        "replaces_key": None,
        "benefit": "No missing canonical catalog function currently justifies another portal.",
        "maintenance_cost": (
            "Large plugin ecosystem and an additional service catalog/control surface."
        ),
        "license": "Apache-2.0",
        "risk": (
            "Would duplicate Project Registry, Integration Registry and corporate catalog truth."
        ),
        "rationale": "Holding remains the canonical project/control-plane catalog.",
        "evidence": ["github:backstage/backstage@v1.55.2"],
    },
    {
        "id": uuid.UUID("47c536d8-294d-42a3-a537-5cef45cd1314"),
        "key": "OPENBAO_SECOND_SECRET_PLANE",
        "tool_name": "OpenBao",
        "capability": "secrets-management",
        "classification": "reject",
        "replaces_key": "SECOND_SECRETS_CONTROL_PLANE",
        "benefit": (
            "No current capability gap versus Google Secret Manager for the selected runtime."
        ),
        "maintenance_cost": "Requires operating another highly sensitive secrets control plane.",
        "license": "MPL-2.0",
        "risk": "Expands credential attack surface and splits the secret source of truth.",
        "rationale": "Google Secret Manager remains canonical for the GCP architecture.",
        "evidence": ["github:openbao/openbao@v2.7.0"],
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
