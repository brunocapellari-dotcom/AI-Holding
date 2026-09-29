resource "google_project_iam_member" "pmo_cloud_build_viewer" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.viewer"
  member  = "serviceAccount:${google_service_account.pmo_worker.email}"

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_job" "cloud_build_collector" {
  count               = var.deploy_service ? 1 : 0
  name                = "${var.service_name}-cloud-build-collector"
  location            = var.region
  deletion_protection = true

  depends_on = [
    google_project_service.required,
    google_project_iam_member.pmo_cloud_build_viewer,
    google_cloud_run_v2_service_iam_member.pmo_invoker,
    google_service_account_iam_member.deployer_act_as_pmo_worker,
  ]

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = !var.deploy_service || startswith(var.image_ref, "${var.region}-docker.pkg.dev/${var.project_id}/")
      error_message = "image_ref must be an immutable Artifact Registry reference in the production project when deploy_service=true."
    }
  }

  template {
    template {
      service_account = google_service_account.pmo_worker.email
      timeout         = "300s"
      max_retries     = 0

      containers {
        image   = var.image_ref
        command = ["python"]
        args    = ["-m", "app.cloud_build_collector"]

        env {
          name  = "CONTROL_PLANE_URL"
          value = google_cloud_run_v2_service.api[0].uri
        }

        env {
          name  = "CONTROL_PLANE_AUDIENCE"
          value = "holding-control-plane"
        }

        env {
          name  = "CLOUD_BUILD_PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "CLOUD_BUILD_REGION"
          value = var.region
        }

        env {
          name  = "CLOUD_BUILD_MAX_BUILDS"
          value = "100"
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_cloud_build_collector_invoker" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.cloud_build_collector[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.worker_scheduler.email}"
}

resource "google_cloud_scheduler_job" "cloud_build_collector" {
  count            = var.deploy_service ? 1 : 0
  name             = "${var.service_name}-cloud-build-collector-schedule"
  description      = "Collect Cloud Build quality state for Holding repositories every five minutes."
  region           = var.region
  schedule         = "2-57/5 * * * *"
  time_zone        = "America/Cuiaba"
  attempt_deadline = "60s"

  retry_config {
    retry_count        = 2
    max_retry_duration = "240s"
  }

  http_target {
    http_method = "POST"
    uri = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.cloud_build_collector[0].name}:run"
    body = base64encode("{}")
    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.worker_scheduler.email
    }
  }

  depends_on = [
    google_cloud_run_v2_job_iam_member.scheduler_cloud_build_collector_invoker,
  ]

  lifecycle {
    prevent_destroy = true
  }
}

output "cloud_build_collector_job" {
  value = var.deploy_service ? google_cloud_run_v2_job.cloud_build_collector[0].name : null
}

output "cloud_build_collector_scheduler" {
  value = var.deploy_service ? google_cloud_scheduler_job.cloud_build_collector[0].name : null
}
