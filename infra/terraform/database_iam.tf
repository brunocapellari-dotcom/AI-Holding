resource "google_project_iam_member" "control_plane_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.control_plane.email}"
}

resource "google_project_iam_member" "control_plane_cloudsql_instance_user" {
  project = var.project_id
  role    = "roles/cloudsql.instanceUser"
  member  = "serviceAccount:${google_service_account.control_plane.email}"
}

resource "google_sql_user" "control_plane_iam" {
  name     = trimsuffix(google_service_account.control_plane.email, ".gserviceaccount.com")
  instance = google_sql_database_instance.postgres.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"

  depends_on = [
    google_project_iam_member.control_plane_cloudsql_client,
    google_project_iam_member.control_plane_cloudsql_instance_user,
  ]
}

output "cloud_sql_iam_database_user" {
  value = google_sql_user.control_plane_iam.name
}


resource "google_service_account" "migration" {
  account_id   = "holding-db-migration"
  display_name = "Holding Database Migration"

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account_iam_member" "deployer_act_as_migration" {
  service_account_id = google_service_account.migration.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.deployer_service_account}"
}

resource "google_project_iam_member" "migration_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.migration.email}"
}

resource "google_project_iam_member" "migration_cloudsql_instance_user" {
  project = var.project_id
  role    = "roles/cloudsql.instanceUser"
  member  = "serviceAccount:${google_service_account.migration.email}"
}

resource "google_sql_user" "migration_iam" {
  name     = trimsuffix(google_service_account.migration.email, ".gserviceaccount.com")
  instance = google_sql_database_instance.postgres.name
  type     = "CLOUD_IAM_SERVICE_ACCOUNT"

  depends_on = [
    google_project_iam_member.migration_cloudsql_client,
    google_project_iam_member.migration_cloudsql_instance_user,
  ]
}

resource "google_secret_manager_secret_iam_member" "migration_database_url_rollback" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.migration.email}"
}

output "migration_runtime_service_account" {
  value = google_service_account.migration.email
}

output "migration_cloud_sql_iam_database_user" {
  value = google_sql_user.migration_iam.name
}
