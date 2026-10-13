variable "github_collector_enabled" {
  type        = bool
  default     = false
  description = "Enable the private-repository GitHub operational collector after an authorized token secret exists."
}

variable "github_collector_token_secret_id" {
  type        = string
  default     = ""
  description = "Secret Manager secret ID containing a read-only GitHub token for the collector."
}

data "google_secret_manager_secret" "github_collector_token" {
  count     = var.github_collector_enabled ? 1 : 0
  project   = var.project_id
  secret_id = var.github_collector_token_secret_id
}

resource "google_secret_manager_secret_iam_member" "pmo_github_collector_token" {
  count     = var.github_collector_enabled ? 1 : 0
  project   = var.project_id
  secret_id = data.google_secret_manager_secret.github_collector_token[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pmo_worker.email}"
}

resource "google_cloud_run_v2_job" "github_collector" {
  count               = var.deploy_service && var.github_collector_enabled ? 1 : 0
  name                = "${var.service_name}-github-collector"
  location            = var.region
  deletion_protection = true

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service_iam_member.pmo_invoker,
    google_secret_manager_secret_iam_member.pmo_github_collector_token,
    google_service_account_iam_member.deployer_act_as_pmo_worker,
  ]

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = !var.github_collector_enabled || length(trimspace(var.github_collector_token_secret_id)) > 0
      error_message = "github_collector_token_secret_id is required when github_collector_enabled=true."
    }

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
        args    = ["-m", "app.github_collector"]

        env {
          name  = "CONTROL_PLANE_URL"
          value = google_cloud_run_v2_service.api[0].uri
        }

        env {
          name  = "CONTROL_PLANE_AUDIENCE"
          value = "holding-control-plane"
        }

        env {
          name  = "GITHUB_COLLECTOR_MAX_PROJECTS"
          value = "100"
        }

        env {
          name = "GITHUB_TOKEN"
          value_source {
            secret_key_ref {
              secret  = data.google_secret_manager_secret.github_collector_token[0].secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_github_collector_invoker" {
  count    = var.deploy_service && var.github_collector_enabled ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_job.github_collector[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.worker_scheduler.email}"
}

resource "google_cloud_scheduler_job" "github_collector" {
  count            = var.deploy_service && var.github_collector_enabled ? 1 : 0
  name             = "${var.service_name}-github-collector-schedule"
  description      = "Collect private GitHub repository and CI state into the Holding every ten minutes."
  region           = var.region
  schedule         = "3,13,23,33,43,53 * * * *"
  time_zone        = "America/Cuiaba"
  attempt_deadline = "60s"

  retry_config {
    retry_count        = 3
    max_retry_duration = "300s"
  }

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.github_collector[0].name}:run"
    body        = base64encode("{}")
    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.worker_scheduler.email
    }
  }

  depends_on = [
    google_cloud_run_v2_job_iam_member.scheduler_github_collector_invoker,
  ]

  lifecycle {
    prevent_destroy = true
  }
}

output "github_collector_job" {
  value = var.deploy_service && var.github_collector_enabled ? google_cloud_run_v2_job.github_collector[0].name : null
}
