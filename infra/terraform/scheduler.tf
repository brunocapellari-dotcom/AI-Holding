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

resource "google_cloud_scheduler_job" "pmo_worker" {
  count       = var.deploy_service ? 1 : 0
  name        = "${var.service_name}-pmo-worker"
  description = "Execute the bounded PMO worker every ten minutes."
  region      = var.region
  schedule    = "*/10 * * * *"
  time_zone   = "Etc/UTC"
  paused      = true

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.pmo_worker[0].name}:run"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.worker_scheduler.email
    }
  }

  retry_config {
    retry_count = 2
  }

  attempt_deadline = "120s"

  lifecycle {
    ignore_changes = [paused]
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_job_iam_member.scheduler_pmo_invoker,
    google_service_account_iam_member.deployer_act_as_worker_scheduler,
  ]
}

resource "google_cloud_scheduler_job" "knowledge_worker" {
  count       = var.deploy_service ? 1 : 0
  name        = "${var.service_name}-knowledge-worker"
  description = "Poll due read-only Knowledge IA maintenance work hourly."
  region      = var.region
  schedule    = "0 * * * *"
  time_zone   = "Etc/UTC"
  paused      = true

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.knowledge_worker[0].name}:run"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.worker_scheduler.email
    }
  }

  retry_config {
    retry_count = 2
  }

  attempt_deadline = "120s"

  lifecycle {
    ignore_changes = [paused]
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_job_iam_member.scheduler_knowledge_invoker,
    google_service_account_iam_member.deployer_act_as_worker_scheduler,
  ]
}

output "pmo_worker_schedule" {
  value = var.deploy_service ? google_cloud_scheduler_job.pmo_worker[0].schedule : null
}

output "knowledge_worker_schedule" {
  value = var.deploy_service ? google_cloud_scheduler_job.knowledge_worker[0].schedule : null
}

output "worker_scheduler_service_account" {
  value = google_service_account.worker_scheduler.email
}
