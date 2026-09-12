resource "google_service_account" "pmo_scheduler" {
  account_id   = "holding-pmo-scheduler"
  display_name = "Holding PMO Scheduler"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "deployer_act_as_pmo_scheduler" {
  service_account_id = google_service_account.pmo_scheduler.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.deployer_service_account}"
}

resource "google_cloud_run_v2_job_iam_member" "pmo_scheduler_invoker" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.pmo_worker[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pmo_scheduler.email}"
}

resource "google_cloud_scheduler_job" "pmo_worker" {
  count       = var.deploy_service ? 1 : 0
  project     = var.project_id
  region      = var.region
  name        = "${var.service_name}-pmo-schedule"
  description = "Fail-closed production trigger for the AI Holding PMO worker."

  schedule         = "*/10 * * * *"
  time_zone        = "Etc/UTC"
  paused           = true
  attempt_deadline = "30s"

  retry_config {
    retry_count          = 1
    min_backoff_duration = "30s"
    max_backoff_duration = "60s"
    max_doublings        = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.pmo_worker[0].name}:run"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.pmo_scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_job_iam_member.pmo_scheduler_invoker,
    google_service_account_iam_member.deployer_act_as_pmo_scheduler,
  ]

  lifecycle {
    prevent_destroy = true
  }
}

output "pmo_scheduler_job" {
  value = var.deploy_service ? google_cloud_scheduler_job.pmo_worker[0].name : null
}

output "pmo_scheduler_service_account" {
  value = google_service_account.pmo_scheduler.email
}
