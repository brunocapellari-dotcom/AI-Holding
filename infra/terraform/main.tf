terraform {
  required_version = ">= 1.7"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "gcs" {}
}

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "southamerica-east1"
}

variable "service_name" {
  type    = string
  default = "holding-control-plane"
}

variable "deploy_service" {
  type    = bool
  default = false
}

variable "image_ref" {
  type        = string
  default     = ""
  description = "Immutable Artifact Registry image reference, preferably by digest. Required when deploy_service=true."
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  required_services = toset([
    "artifactregistry.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
  ])

  deployer_service_account = "github-deployer@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_project_service" "required" {
  for_each           = local.required_services
  service            = each.value
  disable_on_destroy = false
}

resource "google_compute_network" "holding" {
  name                    = "holding-control-plane-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.required]
}

resource "google_compute_subnetwork" "holding" {
  name                     = "holding-control-plane-${var.region}"
  region                   = var.region
  network                  = google_compute_network.holding.id
  ip_cidr_range            = "10.42.0.0/24"
  private_ip_google_access = true
}

resource "google_compute_global_address" "private_services" {
  name          = "holding-private-services"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.holding.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.holding.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services.name]
  depends_on              = [google_project_service.required]
}

resource "google_artifact_registry_repository" "holding" {
  location      = var.region
  repository_id = "holding"
  description   = "Production images for the AI Holding"
  format        = "DOCKER"
  depends_on    = [google_project_service.required]
}

resource "google_service_account" "control_plane" {
  account_id   = "holding-control-plane"
  display_name = "Holding Control Plane"
}

resource "google_service_account_iam_member" "deployer_act_as_control_plane" {
  service_account_id = google_service_account.control_plane.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.deployer_service_account}"
}

resource "google_sql_database_instance" "postgres" {
  name                = "holding-control-plane-pg"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = true

  depends_on = [google_service_networking_connection.private_vpc]

  settings {
    tier              = "db-custom-1-3840"
    edition           = "ENTERPRISE"
    availability_type = "REGIONAL"
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "03:00"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = 14
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 7
      hour         = 4
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = false
    }

    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = google_compute_network.holding.id
      enable_private_path_for_google_cloud_services = true
      ssl_mode                                      = "ENCRYPTED_ONLY"
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_sql_database" "holding" {
  name     = "holding"
  instance = google_sql_database_instance.postgres.name
}

resource "random_password" "db" {
  length           = 40
  special          = true
  override_special = "-_!@#%"
}

resource "google_sql_user" "holding" {
  name     = "holding_app"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db.result
}

resource "google_secret_manager_secret" "database_url" {
  secret_id = "holding-control-plane-database-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = "postgresql+psycopg://${google_sql_user.holding.name}:${urlencode(random_password.db.result)}@${google_sql_database_instance.postgres.private_ip_address}:5432/${google_sql_database.holding.name}?sslmode=require"
}

resource "google_secret_manager_secret_iam_member" "control_plane_database_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.control_plane.email}"
}

resource "google_cloud_run_v2_service" "api" {
  count               = var.deploy_service ? 1 : 0
  name                = var.service_name
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"
  custom_audiences    = ["holding-control-plane"]

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
    service_account = google_service_account.control_plane.email

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.holding.name
        subnetwork = google_compute_subnetwork.holding.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = var.image_ref

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle = true
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "REQUIRE_VERIFIED_IDENTITY"
        value = "true"
      }

      env {
        name  = "VERIFIED_IDENTITY_AUDIENCE"
        value = "holding-control-plane"
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

      startup_probe {
        failure_threshold = 12
        period_seconds    = 5
        timeout_seconds   = 3

        http_get {
          path = "/health"
          port = 8080
        }
      }

      liveness_probe {
        failure_threshold = 3
        period_seconds    = 30
        timeout_seconds   = 3

        http_get {
          path = "/health"
          port = 8080
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job" "migrate" {
  count               = var.deploy_service ? 1 : 0
  name                = "${var.service_name}-migrate"
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
        args    = ["-m", "app.db_migrate"]

        env {
          name  = "ENVIRONMENT"
          value = "production"
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

output "control_plane_url" {
  value = var.deploy_service ? google_cloud_run_v2_service.api[0].uri : null
}

output "migration_job" {
  value = var.deploy_service ? google_cloud_run_v2_job.migrate[0].name : null
}

output "artifact_repository" {
  value = google_artifact_registry_repository.holding.name
}

output "cloud_sql_instance" {
  value = google_sql_database_instance.postgres.connection_name
}
