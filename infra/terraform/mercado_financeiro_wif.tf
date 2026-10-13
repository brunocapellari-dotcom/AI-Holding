locals {
  mercado_financeiro_main_subject = "principal://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/github-actions/subject/repo:brunocapellari-dotcom/Mercado-Financeiro:ref:refs/heads/main"
}

resource "google_iam_workload_identity_pool_provider" "mercado_financeiro_deploy" {
  project                            = var.project_id
  workload_identity_pool_id          = "github-actions"
  workload_identity_pool_provider_id = "mf-deploy-main"
  display_name                       = "Mercado Financeiro deploy"
  description                        = "Keyless deploy trust restricted to Mercado-Financeiro main deploy-paper-shadow workflow."

  attribute_mapping = {
    "google.subject"        = "assertion.sub"
    "attribute.actor"       = "assertion.actor"
    "attribute.repository"  = "assertion.repository"
    "attribute.ref"         = "assertion.ref"
    "attribute.workflow"    = "assertion.job_workflow_ref"
  }

  attribute_condition = <<-EOT
    assertion.repository == "brunocapellari-dotcom/Mercado-Financeiro" &&
    assertion.ref == "refs/heads/main" &&
    assertion.ref_type == "branch" &&
    assertion.job_workflow_ref == "brunocapellari-dotcom/Mercado-Financeiro/.github/workflows/deploy-paper-shadow.yml@refs/heads/main"
  EOT

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "mercado_financeiro_main_impersonates_deployer" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${local.deployer_service_account}"
  role               = "roles/iam.workloadIdentityUser"
  member             = local.mercado_financeiro_main_subject

  depends_on = [google_iam_workload_identity_pool_provider.mercado_financeiro_deploy]
}

output "mercado_financeiro_wif_provider" {
  value = google_iam_workload_identity_pool_provider.mercado_financeiro_deploy.name
}
