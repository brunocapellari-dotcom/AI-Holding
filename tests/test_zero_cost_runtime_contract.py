from pathlib import Path


def test_zero_cost_runtime_is_local_only_and_has_workers() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert '127.0.0.1:8080:8080' in compose
    assert 'ports: ["5432:5432"]' not in compose
    assert "pmo-worker:" in compose
    assert "knowledge-worker:" in compose
    assert "python -m app.bootstrap" in compose


def test_paid_gcp_deploy_is_explicit_opt_in() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "vars.ENABLE_PAID_GCP_DEPLOY == 'true'" in workflow
    assert not Path(".github/workflows/autonomous-workers.yml").exists()
