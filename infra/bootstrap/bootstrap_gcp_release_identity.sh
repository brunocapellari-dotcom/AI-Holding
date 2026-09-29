#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-ai-holding-prod-bc}"
REGION="${REGION:-southamerica-east1}"
RELEASE_SA_ID="${RELEASE_SA_ID:-github-deployer}"
RELEASE_SA="${RELEASE_SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_ID}-tfstate}"

gcloud config set project "${PROJECT_ID}" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
CB_AGENT="service-${PROJECT_NUMBER}@gcp-sa-cloudbuild.iam.gserviceaccount.com"

gcloud services enable   iam.googleapis.com   iamcredentials.googleapis.com   cloudbuild.googleapis.com   cloudresourcemanager.googleapis.com   storage.googleapis.com   --project="${PROJECT_ID}"

if ! gcloud iam service-accounts describe "${RELEASE_SA}"     --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${RELEASE_SA_ID}"     --project="${PROJECT_ID}"     --display-name="AI Holding Cloud Build Release Deployer"
fi

# Release authority remains isolated in one service account. These roles are
# required by the existing Terraform production plan and are never granted to
# the low-privilege ai-build-executor identity.
ROLES=(
  roles/serviceusage.serviceUsageAdmin
  roles/compute.networkAdmin
  roles/servicenetworking.networksAdmin
  roles/artifactregistry.admin
  roles/cloudsql.admin
  roles/cloudscheduler.admin
  roles/secretmanager.admin
  roles/run.admin
  roles/iam.serviceAccountAdmin
)

for role in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}"     --member="serviceAccount:${RELEASE_SA}"     --role="${role}"     --condition=None     --quiet >/dev/null
done

if ! gcloud storage buckets describe "gs://${STATE_BUCKET}"     --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${STATE_BUCKET}"     --project="${PROJECT_ID}"     --location="${REGION}"     --uniform-bucket-level-access     --public-access-prevention
fi

gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning >/dev/null
gcloud storage buckets add-iam-policy-binding "gs://${STATE_BUCKET}"   --member="serviceAccount:${RELEASE_SA}"   --role="roles/storage.objectAdmin" >/dev/null

# Cloud Build may impersonate only this designated release identity.
gcloud iam service-accounts add-iam-policy-binding "${RELEASE_SA}"   --member="serviceAccount:${CB_AGENT}"   --role="roles/iam.serviceAccountTokenCreator"   --project="${PROJECT_ID}"   --quiet >/dev/null

# Keyless Cosign signing uses a short-lived OIDC token from the same release SA.
gcloud iam service-accounts add-iam-policy-binding "${RELEASE_SA}"   --member="serviceAccount:${RELEASE_SA}"   --role="roles/iam.serviceAccountOpenIdTokenCreator"   --project="${PROJECT_ID}"   --quiet >/dev/null

cat <<EOF

CLOUD BUILD RELEASE IDENTITY READY
project: ${PROJECT_ID}
release service account: ${RELEASE_SA}
terraform state: gs://${STATE_BUCKET}

No GitHub OIDC provider and no service-account key were created.
Production execution still requires the approved Cloud Build release trigger.
EOF
