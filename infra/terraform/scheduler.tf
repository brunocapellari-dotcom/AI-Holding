variable "project_number" {
  type        = string
  default     = "868946857614"
  description = "Google Cloud project number used in Workload Identity Federation principal identifiers."
}

locals {
  github_main_scheduler_principal = "principal://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/github-actions/subject/repo:brunocapellari-dotcom/AI-Holding:ref:refs/heads/main"
}

resource "google_service_account" "worker_scheduler" {
  account_id   = "holding-worker-scheduler"
  display_name = "Holding Worker Scheduler"

  depends_on = [google_project_service.required]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "deployer_act_as_worker_scheduler" {
  service_account_id = google_service_account.worker_scheduler.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.deployer_service_account}"
}

resource "google_service_account_iam_member" "github_main_impersonates_worker_scheduler" {
  service_account_id = google_service_account.worker_scheduler.name
  role               = "roles/iam.workloadIdentityUser"
  member             = local.github_main_scheduler_principal
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_pmo_invoker" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.pmo_worker[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.worker_scheduler.email}"
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_knowledge_invoker" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.knowledge_worker[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.worker_scheduler.email}"
}

output "worker_scheduler_service_account" {
  value = google_service_account.worker_scheduler.email
}

output "worker_scheduler_wif_principal" {
  value = local.github_main_scheduler_principal
}
