#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS="${TARGETS:-${ROOT_DIR}/infra/gcp/holding-quality-targets.json}"
PROJECT_ID="ai-holding-prod-bc"
REGION="southamerica-east1"
CONNECTION="ai-github"
EXECUTOR_SA_EMAIL="ai-build-executor@${PROJECT_ID}.iam.gserviceaccount.com"
EXECUTOR_SA="projects/${PROJECT_ID}/serviceAccounts/${EXECUTOR_SA_EMAIL}"
BUILD_FILE="${HOME}/holding-cloud-builds.tsv"

gcloud config set project "${PROJECT_ID}" >/dev/null

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -n1)"
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
  echo "ERROR: no active gcloud account" >&2
  exit 3
fi

gcloud iam service-accounts add-iam-policy-binding "${EXECUTOR_SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --member="user:${ACTIVE_ACCOUNT}" \
  --role="roles/iam.serviceAccountUser" \
  --quiet >/dev/null

python3 - "${TARGETS}" <<'PY' > /tmp/holding-quality-targets.tsv
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
for item in data["targets"]:
    print(item["repo"] + "\t" + item["branch"])
PY

: > "${BUILD_FILE}"

while IFS=$'\t' read -r repo branch; do
  resource_name="$(printf '%s' "${repo}" | tr '[:upper:]_' '[:lower:]-' | tr -cd 'a-z0-9-')"
  trigger="holding-quality-${resource_name}"
  repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${resource_name}"
  escaped_branch="${branch}"

  echo
  echo "== ${repo} =="
  echo "branch=${branch}"

  gcloud builds repositories describe "${resource_name}" \
    --connection="${CONNECTION}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" >/dev/null

  if ! gcloud builds triggers describe "${trigger}" \
      --region="${REGION}" \
      --project="${PROJECT_ID}" >/dev/null 2>&1; then
    gcloud builds triggers create github \
      --name="${trigger}" \
      --repository="${repository}" \
      --branch-pattern="^${escaped_branch}$" \
      --build-config=cloudbuild.yaml \
      --region="${REGION}" \
      --service-account="${EXECUTOR_SA}" \
      --project="${PROJECT_ID}"
  else
    echo "trigger exists: ${trigger}"
  fi

  build_id="$(
    gcloud builds triggers run "${trigger}" \
      --region="${REGION}" \
      --project="${PROJECT_ID}" \
      --branch="${branch}" \
      --format='value(metadata.build.id)'
  )"

  if [[ -z "${build_id}" ]]; then
    echo "ERROR: no build id returned for ${repo}" >&2
    exit 20
  fi

  printf '%s\t%s\t%s\n' "${repo}" "${branch}" "${build_id}" | tee -a "${BUILD_FILE}"
done < /tmp/holding-quality-targets.tsv

echo
echo "============================================================"
echo " 11 HOLDING BUILDS STARTED"
echo "============================================================"
cat "${BUILD_FILE}"
echo
gcloud storage cp "${BUILD_FILE}" \
  "gs://${PROJECT_ID}-ai-execution-evidence/Holding/build-batches/latest.tsv" >/dev/null
echo "Build IDs saved to: ${BUILD_FILE}"
echo "The builds continue in Google Cloud after Cloud Shell is closed."
echo "Status later: bash scripts/status_holding_cloud_builds.sh"
