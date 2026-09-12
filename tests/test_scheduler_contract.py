from pathlib import Path


SCHEDULER_TERRAFORM = Path("infra/terraform/pmo_scheduler.tf")
WORKFLOW = Path(".github/workflows/ci.yml")
BOOTSTRAP = Path("infra/bootstrap/bootstrap_gcp_wif.sh")


def test_scheduler_is_fail_closed_and_uses_dedicated_invoker():
    terraform = SCHEDULER_TERRAFORM.read_text()

    assert 'account_id   = "holding-pmo-scheduler"' in terraform
    assert 'role     = "roles/run.invoker"' in terraform
    assert 'paused           = true' in terraform
    assert 'schedule         = "*/10 * * * *"' in terraform
    assert 'oauth_token {' in terraform
    assert 'service_account_email = google_service_account.pmo_scheduler.email' in terraform
    assert ':run"' in terraform


def test_deployment_resumes_scheduler_only_after_acceptance():
    workflow = WORKFLOW.read_text()

    pause = workflow.index("Pause PMO scheduler during production rollout")
    acceptance = workflow.index("Run controlled PMO production acceptance through scheduler")
    resume = workflow.index("Resume PMO scheduler after production acceptance")

    assert pause < acceptance < resume
    assert "Scheduler-backed PMO acceptance failed closed; PMO scheduling remains paused." in workflow
    assert 'test "${final_state}" = "ENABLED"' in workflow


def test_scheduler_api_and_deployer_permission_are_declared():
    terraform = Path("infra/terraform/main.tf").read_text()
    bootstrap = BOOTSTRAP.read_text()

    assert '"cloudscheduler.googleapis.com"' in terraform
    assert "roles/cloudscheduler.admin" in bootstrap
