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
