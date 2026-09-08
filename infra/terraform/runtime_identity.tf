resource "google_service_account" "pmo_worker" {
  account_id   = "holding-pmo-worker"
  display_name = "Holding PMO Worker"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_cloud_run_v2_service_iam_member" "pmo_invoker" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pmo_worker.email}"
}

resource "google_cloud_run_v2_job" "bootstrap" {
  count               = var.deploy_service ? 1 : 0
  name                = "${var.service_name}-bootstrap"
  location            = var.region
  deletion_protection = true

  depends_on = [
    google_project_service.required,
    google_secret_manager_secret_iam_member.control_plane_database_url,
    google_service_account_iam_member.deployer_act_as_control_plane,
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
      service_account = google_service_account.control_plane.email
      timeout         = "600s"
      max_retries     = 1

      vpc_access {
        network_interfaces {
          network    = google_compute_network.holding.name
          subnetwork = google_compute_subnetwork.holding.name
        }
        egress = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image   = var.image_ref
        command = ["python"]
        args    = ["-m", "app.bootstrap"]

        env {
          name  = "ENVIRONMENT"
          value = "production"
        }

        env {
          name  = "PMO_IDENTITY_ISSUER"
          value = "https://accounts.google.com"
        }

        env {
          name  = "PMO_IDENTITY_SUBJECT"
          value = google_service_account.pmo_worker.unique_id
        }

        env {
          name  = "PMO_IDENTITY_EMAIL"
          value = google_service_account.pmo_worker.email
        }

        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database_url.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

output "bootstrap_job" {
  value = var.deploy_service ? google_cloud_run_v2_job.bootstrap[0].name : null
}

output "pmo_runtime_service_account" {
  value = google_service_account.pmo_worker.email
}

output "pmo_runtime_subject" {
  value = google_service_account.pmo_worker.unique_id
}
