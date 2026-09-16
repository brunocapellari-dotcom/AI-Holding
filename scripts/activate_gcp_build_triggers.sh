#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT_DIR}/infra/gcp/ecosystem-projects.json"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
CONNECTION="${GCP_GITHUB_CONNECTION:-ai-github}"
EXECUTOR_SA_NAME="${EXECUTOR_SA_NAME:-ai-build-executor}"
EXECUTOR_SA="projects/${PROJECT_ID}/serviceAccounts/${EXECUTOR_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure o projeto GCP antes de ativar os triggers" >&2
  exit 2
fi

mapfile -t REPOS < <(python3 - "${MANIFEST}" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as fh:
    data = json.load(fh)
for item in data['projects']:
    print(item['repo'])
PY
)

for repo in "${REPOS[@]}"; do
  resource_name="$(tr '[:upper:]_' '[:lower:]-' <<<"${repo}" | tr -cd 'a-z0-9-')"
  trigger="$(tr '[:upper:]_' '[:lower:]-' <<<"${repo}-main" | tr -cd 'a-z0-9-')"
  repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${resource_name}"

  if gcloud builds triggers describe "${trigger}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "trigger exists: ${trigger}"
    continue
  fi

  gcloud builds triggers create github \
    --name="${trigger}" \
    --repository="${repository}" \
    --branch-pattern='^main$' \
    --build-config='cloudbuild.yaml' \
    --region="${REGION}" \
    --service-account="${EXECUTOR_SA}" \
    --project="${PROJECT_ID}"

done

echo "All main-branch Cloud Build triggers are configured."
