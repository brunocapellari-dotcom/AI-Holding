resource "google_service_account" "pmo_worker" {
  account_id   = "holding-pmo-worker"
  display_name = "Holding PMO Worker"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "knowledge_worker" {
  account_id   = "holding-knowledge-worker"
  display_name = "Holding Knowledge Worker"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "deployer_act_as_pmo_worker" {
  service_account_id = google_service_account.pmo_worker.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.deployer_service_account}"
}

resource "google_service_account_iam_member" "deployer_act_as_knowledge_worker" {
  service_account_id = google_service_account.knowledge_worker.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.deployer_service_account}"
}

resource "google_cloud_run_v2_service_iam_member" "pmo_invoker" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pmo_worker.email}"
}

resource "google_cloud_run_v2_service_iam_member" "knowledge_invoker" {
  count    = var.deploy_service ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.knowledge_worker.email}"
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
          name  = "KNOWLEDGE_IDENTITY_ISSUER"
          value = "https://accounts.google.com"
        }

        env {
          name  = "KNOWLEDGE_IDENTITY_SUBJECT"
          value = google_service_account.knowledge_worker.unique_id
        }

        env {
          name  = "KNOWLEDGE_IDENTITY_EMAIL"
          value = google_service_account.knowledge_worker.email
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

resource "google_cloud_run_v2_job" "pmo_worker" {
  count               = var.deploy_service ? 1 : 0
  name                = "${var.service_name}-pmo-worker"
  location            = var.region
  deletion_protection = true

  depends_on = [
    google_project_service.required,
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
        args    = ["-m", "app.pmo_worker"]

        env {
          name  = "CONTROL_PLANE_URL"
          value = google_cloud_run_v2_service.api[0].uri
        }

        env {
          name  = "CONTROL_PLANE_AUDIENCE"
          value = "holding-control-plane"
        }

        env {
          name  = "PMO_AGENT_KEY"
          value = "PMO_IA"
        }

        env {
          name  = "PMO_MAX_TASKS"
          value = "1"
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "knowledge_worker" {
  count               = var.deploy_service ? 1 : 0
  name                = "${var.service_name}-knowledge-worker"
  location            = var.region
  deletion_protection = true

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service_iam_member.knowledge_invoker,
    google_service_account_iam_member.deployer_act_as_knowledge_worker,
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
      service_account = google_service_account.knowledge_worker.email
      timeout         = "300s"
      max_retries     = 0

      containers {
        image   = var.image_ref
        command = ["python"]
        args    = ["-m", "app.pmo_worker"]

        env {
          name  = "CONTROL_PLANE_URL"
          value = google_cloud_run_v2_service.api[0].uri
        }

        env {
          name  = "CONTROL_PLANE_AUDIENCE"
          value = "holding-control-plane"
        }

        env {
          name  = "PMO_AGENT_KEY"
          value = "KNOWLEDGE_IA"
        }

        env {
          name  = "PMO_MAX_TASKS"
          value = "1"
        }

        env {
          name  = "WORKER_EXECUTION_KINDS"
          value = "knowledge_gap_scan,knowledge_outcome_review"
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "pmo_acceptance" {
  count               = var.deploy_service ? 1 : 0
  name                = "${var.service_name}-pmo-acceptance"
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
      timeout         = "300s"
      max_retries     = 0

      vpc_access {
        network_interfaces {
          network    = google_compute_network.holding.name
          subnetwork = google_compute_subnetwork.holding.name
        }
        egress = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image   = var.image_ref
        command = ["python", "-m", "app.pmo_acceptance"]
        args    = ["status"]

        env {
          name  = "ENVIRONMENT"
          value = "production"
        }

        env {
          name  = "RELEASE_ID"
          value = var.image_ref
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

resource "google_cloud_run_v2_job" "knowledge_acceptance" {
  count               = var.deploy_service ? 1 : 0
  name                = "${var.service_name}-knowledge-acceptance"
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
      timeout         = "300s"
      max_retries     = 0

      vpc_access {
        network_interfaces {
          network    = google_compute_network.holding.name
          subnetwork = google_compute_subnetwork.holding.name
        }
        egress = "PRIVATE_RANGES_ONLY"
      }

      containers {
        image   = var.image_ref
        command = ["python", "-m", "app.knowledge_acceptance"]
        args    = ["status"]

        env {
          name  = "ENVIRONMENT"
          value = "production"
        }

        env {
          name  = "RELEASE_ID"
          value = var.image_ref
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

output "pmo_worker_job" {
  value = var.deploy_service ? google_cloud_run_v2_job.pmo_worker[0].name : null
}

output "knowledge_worker_job" {
  value = var.deploy_service ? google_cloud_run_v2_job.knowledge_worker[0].name : null
}

output "pmo_acceptance_job" {
  value = var.deploy_service ? google_cloud_run_v2_job.pmo_acceptance[0].name : null
}

output "knowledge_acceptance_job" {
  value = var.deploy_service ? google_cloud_run_v2_job.knowledge_acceptance[0].name : null
}

output "pmo_runtime_service_account" {
  value = google_service_account.pmo_worker.email
}

output "pmo_runtime_subject" {
  value = google_service_account.pmo_worker.unique_id
}

output "knowledge_runtime_service_account" {
  value = google_service_account.knowledge_worker.email
}

output "knowledge_runtime_subject" {
  value = google_service_account.knowledge_worker.unique_id
}
