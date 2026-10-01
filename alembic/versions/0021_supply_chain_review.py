"""seed 2026-09-28 supply-chain and GitHub review decisions

Revision ID: 0021_supply_chain_review
Revises: 0020_corporate_registry_baseline
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021_supply_chain_review"
down_revision: str | None = "0020_corporate_registry_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TOOL_DECISIONS = (
    {
        "id": uuid.UUID("35ec2802-5c88-4a0a-80dc-00ac3ab94193"),
        "key": "CLOUD_BUILD_VERIFIED_PROVENANCE",
        "tool_name": "Google Cloud Build verified provenance",
        "capability": "software-supply-chain-provenance",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": (
            "Generates verifiable provenance for Artifact Registry images and fails the build "
            "when requested provenance is not produced."
        ),
        "maintenance_cost": "Native Cloud Build capability; no additional control plane.",
        "license": "managed-service",
        "risk": (
            "Provenance only covers artifacts produced through the configured Cloud Build path; "
            "release policy must reject unprovenanced images."
        ),
        "rationale": (
            "The Holding already standardizes execution on Google Cloud, so native verified "
            "provenance adds supply-chain evidence without reintroducing GitHub Actions."
        ),
        "evidence": [
            "cloudbuild.yaml",
            (
                "https://cloud.google.com/build/docs/securing-builds/"
                "generate-validate-build-provenance"
            ),
        ],
    },
    {
        "id": uuid.UUID("41812dd5-cf89-45bb-aaeb-8f6fdc147f71"),
        "key": "COSIGN_RELEASE_IDENTITY",
        "tool_name": "Sigstore Cosign",
        "capability": "container-signing-and-verification",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": (
            "Adds cryptographic release identity to immutable OCI digests and enables independent "
            "verification of the service account that promoted an image."
        ),
        "maintenance_cost": "One bounded signing/verification step during release promotion.",
        "license": "Apache-2.0",
        "risk": (
            "Signing must use short-lived identity tokens or managed KMS; static private signing "
            "keys are prohibited."
        ),
        "rationale": (
            "Cosign closes the signed-release gap already identified by the open-source intake "
            "policy and complements, rather than replaces, Cloud Build provenance."
        ),
        "evidence": [
            "github:sigstore/cosign@v3.1.3",
            (
                "https://cloud.google.com/build/docs/building/"
                "build-containers#signing-container-images"
            ),
        ],
    },
    {
        "id": uuid.UUID("b77e374a-7f86-4aa9-8599-004353881b1f"),
        "key": "OPENSSF_SCORECARD_EXTERNAL_INTAKE",
        "tool_name": "OpenSSF Scorecard",
        "capability": "external-repository-security-posture",
        "classification": "adopt",
        "replaces_key": None,
        "benefit": (
            "Provides a repeatable upstream repository posture signal before critical open-source "
            "components are promoted into the ecosystem."
        ),
        "maintenance_cost": "Run during intake/re-evaluation, not as another application runtime.",
        "license": "Apache-2.0",
        "risk": (
            "Scores are heuristics and never replace license review, CVE analysis or code review."
        ),
        "rationale": (
            "The existing intake policy already requires Scorecard; this records it as the "
            "canonical upstream-posture tool without duplicating Trivy, Semgrep or Gitleaks."
        ),
        "evidence": [
            "docs/security/OPEN_SOURCE_INTAKE_GATE.md",
            "github:ossf/scorecard@v5.5.0",
        ],
    },
    {
        "id": uuid.UUID("3d8aeb5a-aac1-4eb0-b379-c0b6a56f03ac"),
        "key": "SLSA_GITHUB_GENERATOR_FOR_HOLDING",
        "tool_name": "SLSA GitHub Generator",
        "capability": "software-supply-chain-provenance",
        "classification": "reject",
        "replaces_key": None,
        "benefit": "No incremental benefit over the selected Cloud Build provenance path.",
        "maintenance_cost": (
            "Would restore a GitHub Actions dependency to the canonical release chain."
        ),
        "license": "Apache-2.0",
        "risk": (
            "Creates a parallel provenance implementation and conflicts with the "
            "GCP execution decision."
        ),
        "rationale": (
            "The project is GitHub-Actions-centric and its own repository points new users toward "
            "GitHub artifact attestations; the Holding instead uses Cloud Build native provenance."
        ),
        "evidence": [
            "github:slsa-framework/slsa-github-generator@v2.1.0",
            "cloudbuild.yaml",
        ],
    },
    {
        "id": uuid.UUID("60e0ec23-8c3d-4f5e-8161-e06ba1077f3b"),
        "key": "PREFECT_PARALLEL_HOLDING_ORCHESTRATOR",
        "tool_name": "Prefect",
        "capability": "workflow-orchestration",
        "classification": "reject",
        "replaces_key": None,
        "benefit": (
            "Strong workflow platform, but no uncovered Holding requirement currently justifies it."
        ),
        "maintenance_cost": (
            "Adds another orchestration/runtime state plane beside PMO and Cloud Scheduler."
        ),
        "license": "Apache-2.0",
        "risk": "Split execution truth and overlapping retries/scheduling semantics.",
        "rationale": (
            "Do not add beside the current stack; Temporal remains the only replacement benchmark."
        ),
        "evidence": ["github:PrefectHQ/prefect@3.8.7"],
    },
    {
        "id": uuid.UUID("578a81dd-94b6-46ca-a68a-5a779589cc1a"),
        "key": "DAGSTER_PARALLEL_HOLDING_ORCHESTRATOR",
        "tool_name": "Dagster",
        "capability": "data-and-workflow-orchestration",
        "classification": "reject",
        "replaces_key": None,
        "benefit": (
            "Strong asset-oriented orchestration, but the Holding is not an "
            "asset-orchestrator product."
        ),
        "maintenance_cost": "Additional control plane, metadata model and operational surface.",
        "license": "Apache-2.0",
        "risk": "Duplicates project/collector/workflow ownership and increases tool sprawl.",
        "rationale": (
            "Use in a project only if its asset model proves necessary; not in the Holding core."
        ),
        "evidence": ["github:dagster-io/dagster@1.13.24"],
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
