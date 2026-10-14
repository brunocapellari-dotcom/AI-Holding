#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
CONNECTION="${GCP_GITHUB_CONNECTION:-ai-github}"
REPOSITORY_RESOURCE="${REPOSITORY_RESOURCE:-ai-holding}"
QUALITY_TRIGGER="${QUALITY_TRIGGER:-ai-holding-quality-manual}"
CANDIDATE_TRIGGER="${CANDIDATE_TRIGGER:-ai-holding-candidate-manual}"
RELEASE_TRIGGER="${RELEASE_TRIGGER:-ai-holding-release-manual}"
ENABLE_PAID_GCP_DEPLOY="${ENABLE_PAID_GCP_DEPLOY:-false}"
QUALITY_SA_EMAIL="${QUALITY_SA_EMAIL:-ai-build-executor@${PROJECT_ID}.iam.gserviceaccount.com}"
RELEASE_SA_EMAIL="${RELEASE_SA_EMAIL:-github-deployer@${PROJECT_ID}.iam.gserviceaccount.com}"
QUALITY_SA="projects/${PROJECT_ID}/serviceAccounts/${QUALITY_SA_EMAIL}"
RELEASE_SA="projects/${PROJECT_ID}/serviceAccounts/${RELEASE_SA_EMAIL}"
REPOSITORY="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${REPOSITORY_RESOURCE}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure PROJECT_ID or gcloud project first" >&2
  exit 2
fi

gcloud builds repositories describe "${REPOSITORY_RESOURCE}"   --connection="${CONNECTION}"   --region="${REGION}"   --project="${PROJECT_ID}" >/dev/null

gcloud iam service-accounts describe "${QUALITY_SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null
if [[ "${ENABLE_PAID_GCP_DEPLOY}" == "true" ]]; then
  gcloud iam service-accounts describe "${RELEASE_SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null
fi

if ! gcloud builds triggers describe "${QUALITY_TRIGGER}"     --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud builds triggers create manual     --name="${QUALITY_TRIGGER}"     --repository="${REPOSITORY}"     --branch=main     --build-config=cloudbuild.yaml     --region="${REGION}"     --service-account="${QUALITY_SA}"     --project="${PROJECT_ID}"
else
  echo "trigger exists: ${QUALITY_TRIGGER}"
fi

if [[ "${ENABLE_PAID_GCP_DEPLOY}" == "true" ]]; then
  # Release candidate: same quality gate plus Artifact Registry image with
  # Cloud Build provenance and GCS build-id/source-commit evidence. Manual and
  # approval-gated so the zero-cost quality path never persists artifacts.
  if ! gcloud builds triggers describe "${CANDIDATE_TRIGGER}"     --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud builds triggers create manual     --name="${CANDIDATE_TRIGGER}"     --repository="${REPOSITORY}"     --branch=main     --build-config=cloudbuild.candidate.yaml     --region="${REGION}"     --service-account="${QUALITY_SA}"     --require-approval     --project="${PROJECT_ID}"
  else
    echo "trigger exists: ${CANDIDATE_TRIGGER}"
  fi

  if ! gcloud builds triggers describe "${RELEASE_TRIGGER}"     --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud builds triggers create manual     --name="${RELEASE_TRIGGER}"     --repository="${REPOSITORY}"     --branch=main     --build-config=cloudbuild.release.yaml     --region="${REGION}"     --service-account="${RELEASE_SA}"     --require-approval     --project="${PROJECT_ID}"
  else
    echo "trigger exists: ${RELEASE_TRIGGER}"
  fi
  
else
  echo "paid release trigger remains disabled (zero-cost path)"
fi

cat <<EOF

HOLDING MANUAL GATES: READY

Quality trigger:
  ${QUALITY_TRIGGER}
  service account: ${QUALITY_SA_EMAIL}

Quality can run against an exact commit:
  gcloud builds triggers run ${QUALITY_TRIGGER} --region=${REGION} --sha=<COMMIT_SHA> --project=${PROJECT_ID}

Paid release candidate (${CANDIDATE_TRIGGER}, cloudbuild.candidate.yaml) and
production promotion (${RELEASE_TRIGGER}) are disabled by default. Set ENABLE_PAID_GCP_DEPLOY=true only after explicit owner approval.
EOF
