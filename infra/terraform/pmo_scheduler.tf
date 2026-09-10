variable "enable_pmo_scheduler" {
  type        = bool
  default     = false
  description = "Provision the bounded PMO Cloud Scheduler trigger. Disabled by default."
}

variable "pmo_scheduler_paused" {
  type        = bool
  default     = true
  description = "Keep the PMO schedule paused. Activation requires an explicit false value."
}

variable "pmo_scheduler_schedule" {
  type        = string
  default     = "*/15 * * * *"
  description = "Unix-cron cadence for the bounded PMO worker when scheduling is explicitly enabled."
}

resource "google_project_service" "cloudscheduler" {
  count              = var.enable_pmo_scheduler ? 1 : 0
  service            = "cloudscheduler.googleapis.com"
  disable_on_destroy = false
}

resource "google_service_account" "pmo_scheduler" {
  count        = var.enable_pmo_scheduler ? 1 : 0
  account_id   = "holding-pmo-scheduler"
  display_name = "Holding PMO Scheduler"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "deployer_act_as_pmo_scheduler" {
  count              = var.enable_pmo_scheduler ? 1 : 0
  service_account_id = google_service_account.pmo_scheduler[0].name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.deployer_service_account}"
}

resource "google_cloud_run_v2_job_iam_member" "pmo_scheduler_invoker" {
  count    = var.enable_pmo_scheduler && var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.pmo_worker[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pmo_scheduler[0].email}"
}

resource "google_cloud_scheduler_job" "pmo_worker" {
  count            = var.enable_pmo_scheduler && var.deploy_service ? 1 : 0
  project          = var.project_id
  region           = var.region
  name             = "${var.service_name}-pmo-schedule"
  description      = "Bounded scheduler trigger for the authenticated PMO Cloud Run job."
  schedule         = var.pmo_scheduler_schedule
  time_zone        = "Etc/UTC"
  paused           = var.pmo_scheduler_paused
  attempt_deadline = "300s"

  retry_config {
    retry_count          = 0
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "5s"
    max_doublings        = 0
  }

  http_target {
    http_method = "POST"
    uri = format(
      "https://run.googleapis.com/v2/projects/%s/locations/%s/jobs/%s:run",
      var.project_id,
      var.region,
      google_cloud_run_v2_job.pmo_worker[0].name,
    )
    body = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.pmo_scheduler[0].email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_project_service.cloudscheduler,
    google_cloud_run_v2_job.pmo_worker,
    google_cloud_run_v2_job_iam_member.pmo_scheduler_invoker,
    google_service_account_iam_member.deployer_act_as_pmo_scheduler,
  ]

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = var.enable_pmo_scheduler
      error_message = "PMO scheduler must remain absent unless enable_pmo_scheduler is explicitly true."
    }
  }
}

output "pmo_scheduler_name" {
  value = var.enable_pmo_scheduler && var.deploy_service ? google_cloud_scheduler_job.pmo_worker[0].name : null
}

output "pmo_scheduler_paused" {
  value = var.enable_pmo_scheduler && var.deploy_service ? google_cloud_scheduler_job.pmo_worker[0].paused : null
}
