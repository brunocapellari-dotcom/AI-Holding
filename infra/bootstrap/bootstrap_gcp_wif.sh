#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-ai-holding-prod-bc}"
REGION="${REGION:-southamerica-east1}"
REPO="${REPO:-brunocapellari-dotcom/AI-Holding}"
POOL_ID="${POOL_ID:-github-actions}"
PROVIDER_ID="${PROVIDER_ID:-ai-holding-main}"
DEPLOY_SA_ID="${DEPLOY_SA_ID:-github-deployer}"
STATE_BUCKET="${STATE_BUCKET:-${PROJECT_ID}-tfstate}"

log() { printf '\n[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

log "Selecting project ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

log "Enabling bootstrap APIs"
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT_ID}"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
DEPLOY_SA_EMAIL="${DEPLOY_SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "${DEPLOY_SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  log "Creating deploy service account"
  gcloud iam service-accounts create "${DEPLOY_SA_ID}" \
    --project="${PROJECT_ID}" \
    --display-name="AI Holding GitHub Deployer"
else
  log "Deploy service account already exists"
fi

if ! gcloud iam workload-identity-pools describe "${POOL_ID}" --project="${PROJECT_ID}" --location=global >/dev/null 2>&1; then
  log "Creating Workload Identity Pool"
  gcloud iam workload-identity-pools create "${POOL_ID}" \
    --project="${PROJECT_ID}" \
    --location=global \
    --display-name="GitHub Actions"
else
  log "Workload Identity Pool already exists"
fi

if ! gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" --project="${PROJECT_ID}" --location=global --workload-identity-pool="${POOL_ID}" >/dev/null 2>&1; then
  log "Creating GitHub OIDC provider restricted to ${REPO} main"
  gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
    --project="${PROJECT_ID}" \
    --location=global \
    --workload-identity-pool="${POOL_ID}" \
    --display-name="AI Holding main branch" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository == '${REPO}' && assertion.ref == 'refs/heads/main'"
else
  log "GitHub OIDC provider already exists"
fi

POOL_NAME="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}"
PRINCIPAL="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${REPO}"

log "Granting Workload Identity User on deploy service account"
gcloud iam service-accounts add-iam-policy-binding "${DEPLOY_SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="${PRINCIPAL}" >/dev/null

ROLES=(
  roles/serviceusage.serviceUsageAdmin
  roles/compute.networkAdmin
  roles/servicenetworking.networksAdmin
  roles/artifactregistry.admin
  roles/cloudsql.admin
  roles/secretmanager.admin
  roles/run.admin
  roles/iam.serviceAccountAdmin
)

log "Granting production deployment roles"
for role in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DEPLOY_SA_EMAIL}" \
    --role="${role}" \
    --condition=None >/dev/null
done

if ! gcloud storage buckets describe "gs://${STATE_BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  log "Creating Terraform state bucket"
  gcloud storage buckets create "gs://${STATE_BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access \
    --public-access-prevention
else
  log "Terraform state bucket already exists"
fi

gcloud storage buckets update "gs://${STATE_BUCKET}" --versioning >/dev/null

gcloud storage buckets add-iam-policy-binding "gs://${STATE_BUCKET}" \
  --member="serviceAccount:${DEPLOY_SA_EMAIL}" \
  --role="roles/storage.objectAdmin" >/dev/null

PROVIDER_NAME="$(gcloud iam workload-identity-pools providers describe "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location=global \
  --workload-identity-pool="${POOL_ID}" \
  --format='value(name)')"

cat <<EOF

BOOTSTRAP COMPLETE

GCP_PROJECT_ID=${PROJECT_ID}
GCP_REGION=${REGION}
GCP_WIF_PROVIDER=${PROVIDER_NAME}
GCP_DEPLOY_SERVICE_ACCOUNT=${DEPLOY_SA_EMAIL}
TF_STATE_BUCKET=${STATE_BUCKET}

Add the provider and service-account values as GitHub repository variables before enabling production deployment.
No long-lived service-account key was created.
EOF
