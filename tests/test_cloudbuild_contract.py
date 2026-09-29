from __future__ import annotations

import re
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


_ALLOWED_CLOUD_BUILD_SUBSTITUTIONS = {
    "PROJECT_ID",
    "PROJECT_NUMBER",
    "BUILD_ID",
    "LOCATION",
    "TRIGGER_NAME",
    "COMMIT_SHA",
    "REVISION_ID",
    "SHORT_SHA",
    "REPO_NAME",
    "REPO_FULL_NAME",
    "BRANCH_NAME",
    "TAG_NAME",
    "REF_NAME",
    "TRIGGER_BUILD_CONFIG_PATH",
    "SERVICE_ACCOUNT_EMAIL",
    "SERVICE_ACCOUNT",
}


def test_cloudbuild_yaml_does_not_leak_shell_variables_into_substitution() -> None:
    pattern = re.compile(r"(?<!\$)\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")
    for path in ("cloudbuild.yaml", "cloudbuild.release.yaml"):
        invalid: list[str] = []
        for match in pattern.finditer(_read(path)):
            name = match.group(1) or match.group(2)
            if name not in _ALLOWED_CLOUD_BUILD_SUBSTITUTIONS and not name.startswith("_"):
                invalid.append(name)
        assert invalid == [], f"{path} has unescaped shell variables: {invalid}"



def test_ci_toolchain_uses_official_terraform_stage() -> None:
    dockerfile = _read("Dockerfile.ci")
    assert "FROM hashicorp/terraform:1.9.8 AS terraform" in dockerfile
    assert "COPY --from=terraform /bin/terraform /usr/local/bin/terraform" in dockerfile
    assert "releases.hashicorp.com" not in dockerfile
    assert "terraform.zip" not in dockerfile



def test_github_actions_is_manual_diagnostic_only() -> None:
    workflow = _read(".github/workflows/ci.yml")
    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "branches: [main]" not in workflow
    assert "deploy-production" not in workflow
    assert "google-github-actions/auth" not in workflow
    assert "terraform apply" not in workflow
    assert "gcloud run jobs execute" not in workflow
    assert "manual diagnostic fallback only" in workflow
