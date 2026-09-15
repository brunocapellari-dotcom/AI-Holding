resource "google_project_iam_member" "deployer_cloudscheduler_admin" {
  project = var.project_id
  role    = "roles/cloudscheduler.admin"
  member  = "serviceAccount:${local.deployer_service_account}"

  depends_on = [google_project_service.required]
}
