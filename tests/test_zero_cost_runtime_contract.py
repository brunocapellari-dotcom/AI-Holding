from pathlib import Path


def test_zero_cost_runtime_is_local_only_and_has_workers() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert '127.0.0.1:8080:8080' in compose
    assert 'ports: ["5432:5432"]' not in compose
    assert "pmo-worker:" in compose
    assert "knowledge-worker:" in compose
    assert "python -m app.bootstrap" in compose


def test_cloud_build_is_the_canonical_quality_runner() -> None:
    cloudbuild = Path("cloudbuild.yaml").read_text(encoding="utf-8")
    triggers = Path("scripts/activate_holding_gcp_triggers.sh").read_text(encoding="utf-8")

    assert "full-project-gate" in cloudbuild
    assert "persist-build-evidence" not in cloudbuild
    assert "\nimages:\n" not in cloudbuild
    assert 'ENABLE_PAID_GCP_DEPLOY="${ENABLE_PAID_GCP_DEPLOY:-false}"' in triggers
    assert not Path(".github/workflows/ci.yml").exists()
    assert not Path(".github/workflows/autonomous-workers.yml").exists()
