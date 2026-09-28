#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
CONNECTION="${GCP_GITHUB_CONNECTION:-ai-github}"
REPOSITORY_RESOURCE="${REPOSITORY_RESOURCE:-ai-holding}"
QUALITY_TRIGGER="${QUALITY_TRIGGER:-ai-holding-quality-manual}"
RELEASE_TRIGGER="${RELEASE_TRIGGER:-ai-holding-release-manual}"
QUALITY_SA="${QUALITY_SA:-ai-build-executor@${PROJECT_ID}.iam.gserviceaccount.com}"
RELEASE_SA="${RELEASE_SA:-github-deployer@${PROJECT_ID}.iam.gserviceaccount.com}"
REPOSITORY="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${REPOSITORY_RESOURCE}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure PROJECT_ID or gcloud project first" >&2
  exit 2
fi

gcloud builds repositories describe "${REPOSITORY_RESOURCE}"   --connection="${CONNECTION}"   --region="${REGION}"   --project="${PROJECT_ID}" >/dev/null

for sa in "${QUALITY_SA}" "${RELEASE_SA}"; do
  gcloud iam service-accounts describe "${sa}" --project="${PROJECT_ID}" >/dev/null
done

if ! gcloud builds triggers describe "${QUALITY_TRIGGER}"     --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud builds triggers create manual     --name="${QUALITY_TRIGGER}"     --repository="${REPOSITORY}"     --branch=main     --build-config=cloudbuild.yaml     --region="${REGION}"     --service-account="${QUALITY_SA}"     --project="${PROJECT_ID}"
else
  echo "trigger exists: ${QUALITY_TRIGGER}"
fi

if ! gcloud builds triggers describe "${RELEASE_TRIGGER}"     --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud builds triggers create manual     --name="${RELEASE_TRIGGER}"     --repository="${REPOSITORY}"     --branch=main     --build-config=cloudbuild.release.yaml     --region="${REGION}"     --service-account="${RELEASE_SA}"     --project="${PROJECT_ID}"
else
  echo "trigger exists: ${RELEASE_TRIGGER}"
fi

cat <<EOF

HOLDING MANUAL GATES: READY

Quality trigger:
  ${QUALITY_TRIGGER}
  service account: ${QUALITY_SA}

Release trigger:
  ${RELEASE_TRIGGER}
  service account: ${RELEASE_SA}

Quality can run against an exact commit:
  gcloud builds triggers run ${QUALITY_TRIGGER} --region=${REGION} --sha=<COMMIT_SHA> --project=${PROJECT_ID}

Production promotion must use the exact SHA and candidate Build ID:
  gcloud builds triggers run ${RELEASE_TRIGGER} --region=${REGION} --sha=<COMMIT_SHA> --project=${PROJECT_ID} \
    --substitutions=_CANDIDATE_BUILD_ID=<QUALITY_BUILD_ID>,_SOURCE_COMMIT_SHA=<COMMIT_SHA>
EOF
