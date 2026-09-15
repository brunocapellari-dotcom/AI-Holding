from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_autonomous_workers_use_keyless_branch_bound_identity():
    workflow = (ROOT / ".github/workflows/autonomous-workers.yml").read_text(encoding="utf-8")
    terraform = (ROOT / "infra/terraform/scheduler.tf").read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "holding-worker-scheduler@" in workflow
    assert "google-github-actions/auth@v2" in workflow
    assert "activate-service-account" not in workflow
    assert "GOOGLE_APPLICATION_CREDENTIALS_JSON" not in workflow

    assert "roles/iam.workloadIdentityUser" in terraform
    assert "repo:brunocapellari-dotcom/AI-Holding:ref:refs/heads/main" in terraform
    assert 'role     = "roles/run.invoker"' in terraform


def test_legacy_cloud_scheduler_is_fail_closed_by_default():
    terraform = (ROOT / "infra/terraform/scheduler.tf").read_text(encoding="utf-8")

    assert 'variable "legacy_cloud_scheduler_enabled"' in terraform
    assert "default     = false" in terraform
    assert "var.legacy_cloud_scheduler_enabled" in terraform


def test_scheduler_boundary_never_grants_broad_admin_roles():
    terraform = (ROOT / "infra/terraform/scheduler.tf").read_text(encoding="utf-8")
    forbidden = (
        "roles/owner",
        "roles/editor",
        "roles/run.admin",
        "roles/iam.serviceAccountAdmin",
        "roles/cloudscheduler.admin",
    )
    for role in forbidden:
        assert role not in terraform
