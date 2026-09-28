#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="ai-holding-prod-bc"
REGION="southamerica-east1"
FILE="${1:-${HOME}/holding-cloud-builds.tsv}"

if [[ ! -f "${FILE}" ]]; then
  echo "No local build-id file found. Showing recent Holding builds instead."
  gcloud builds list \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --limit=30 \
    --format='table(id,status,createTime,substitutions.REPO_NAME,substitutions.BRANCH_NAME)'
  exit 0
fi

printf '%-38s %-12s %s\n' "PROJECT" "STATUS" "BUILD_ID"
while IFS=$'\t' read -r repo branch build_id; do
  status="$(
    gcloud builds describe "${build_id}" \
      --project="${PROJECT_ID}" \
      --region="${REGION}" \
      --format='value(status)' 2>/dev/null || printf 'UNKNOWN'
  )"
  printf '%-38s %-12s %s\n' "${repo}" "${status}" "${build_id}"
done < "${FILE}"
