from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_quality_cloud_build_is_low_privilege_and_provenance_gated() -> None:
    config = _read("cloudbuild.yaml")
    assert "ai-build-executor@" in config
    assert "requestedVerifyOption: VERIFIED" in config
    assert 'images:' in config
    assert 'source-commit.txt' in config
    assert 'build-id.txt' in config
    assert 'gitleaks.json' in config
    assert 'sbom.cdx.json' in config
    assert 'trivy-image.json' in config


def test_release_cloud_build_reuses_exact_candidate_and_release_identity() -> None:
    config = _read("cloudbuild.release.yaml")
    assert "github-deployer@" in config
    assert "_CANDIDATE_BUILD_ID" in config
    assert "_SOURCE_COMMIT_SHA" in config
    assert "--show-provenance" in config
    assert "candidate-source-commit.txt" in config
    assert "cosign/cosign:v3.1.3" in config
    assert "--certificate-oidc-issuer=" in config
    assert "scripts/deploy_release_candidate.sh" in config
    assert "docker build" not in config


def test_execution_fabric_has_bounded_build_and_release_identities() -> None:
    bootstrap = _read("scripts/bootstrap_gcp_execution_fabric.sh")
    assert 'EXECUTOR_SA_NAME="${EXECUTOR_SA_NAME:-ai-build-executor}"' in bootstrap
    assert 'RELEASE_SA_NAME="${RELEASE_SA_NAME:-github-deployer}"' in bootstrap
    assert "roles/iam.serviceAccountTokenCreator" in bootstrap
    assert "roles/iam.serviceAccountOpenIdTokenCreator" in bootstrap
    assert "containeranalysis.googleapis.com" in bootstrap


def test_holding_manual_gates_are_separated_by_service_account() -> None:
    script = _read("scripts/activate_holding_gcp_triggers.sh")
    assert "ai-holding-quality-manual" in script
    assert "ai-holding-release-manual" in script
    assert "ai-build-executor@" in script
    assert "github-deployer@" in script
    assert "--build-config=cloudbuild.yaml" in script
    assert "--build-config=cloudbuild.release.yaml" in script
    assert "--require-approval" in script
