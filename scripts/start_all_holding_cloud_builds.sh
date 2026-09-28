#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGETS="${TARGETS:-${ROOT_DIR}/infra/gcp/holding-quality-targets.json}"
PROJECT_ID="ai-holding-prod-bc"
REGION="southamerica-east1"
CONNECTION="ai-github"
EXECUTOR_SA="projects/${PROJECT_ID}/serviceAccounts/ai-build-executor@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud config set project "${PROJECT_ID}" >/dev/null

python3 - "${TARGETS}" <<'PY' > /tmp/holding-quality-targets.tsv
import json
import sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for item in data["targets"]:
    print(item["repo"] + "\t" + item["branch"])
PY

BUILD_FILE="${HOME}/holding-cloud-builds.tsv"
: > "${BUILD_FILE}"

while IFS=$'\t' read -r repo branch; do
  resource_name="$(printf '%s' "${repo}" | tr '[:upper:]_' '[:lower:]-' | tr -cd 'a-z0-9-')"
  trigger="holding-quality-${resource_name}"
  repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${resource_name}"
  escaped_branch="$(python3 -c 'import re,sys; print(re.escape(sys.argv[1]))' "${branch}")"

  echo
  echo "== ${repo} =="
  echo "branch=${branch}"

  gcloud builds repositories describe "${resource_name}" \
    --connection="${CONNECTION}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" >/dev/null

  if ! gcloud builds triggers describe "${trigger}" \
      --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
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
column -t -s 
echo
echo "The builds are now running in Google Cloud and continue after Cloud Shell is closed."
gcloud storage cp "${BUILD_FILE}" "gs://${PROJECT_ID}-ai-execution-evidence/Holding/build-batches/latest.tsv" >/dev/null
echo "Build IDs saved to: ${BUILD_FILE}"
echo "Use later: bash scripts/status_holding_cloud_builds.sh"
\t' "${BUILD_FILE}" 2>/dev/null || cat "${BUILD_FILE}"
echo
echo "The builds are now running in Google Cloud and continue after Cloud Shell is closed."
echo "Use: bash scripts/status_holding_cloud_builds.sh"
