#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT_DIR}/infra/gcp/ecosystem-projects.json"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
CONNECTION="${GCP_GITHUB_CONNECTION:-ai-github}"
EXECUTOR_SA_NAME="${EXECUTOR_SA_NAME:-ai-build-executor}"
EXECUTOR_SA="projects/${PROJECT_ID}/serviceAccounts/${EXECUTOR_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
CANDIDATE_REPO="${CANDIDATE_REPO:-}"
RUN_NOW="${RUN_NOW:-true}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure o projeto GCP antes de ativar os candidate gates" >&2
  exit 2
fi

for cmd in gcloud python3 sha256sum; do
  command -v "${cmd}" >/dev/null || { echo "ERROR: ${cmd} nao encontrado" >&2; exit 3; }
done

mapfile -t CANDIDATES < <(python3 - "${MANIFEST}" "${CANDIDATE_REPO}" <<'PY'
import json, sys
manifest, wanted = sys.argv[1], sys.argv[2]
with open(manifest, encoding="utf-8") as fh:
    data = json.load(fh)
for item in data["projects"]:
    branch = item.get("candidate_branch")
    if not branch:
        continue
    if wanted and item["repo"] != wanted:
        continue
    print(f'{item["repo"]}\t{branch}')
PY
)

if [[ "${#CANDIDATES[@]}" -eq 0 ]]; then
  echo "No candidate branches configured for the requested scope." >&2
  exit 4
fi

for row in "${CANDIDATES[@]}"; do
  IFS=$'\t' read -r repo branch <<<"${row}"

  resource_name="$(tr '[:upper:]_' '[:lower:]-' <<<"${repo}" | tr -cd 'a-z0-9-')"
  repository="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${resource_name}"

  normalized_branch="$(tr '/[:upper:]_' '-[:lower:]-' <<<"${branch}" | tr -cd 'a-z0-9-')"
  fingerprint="$(printf '%s:%s' "${repo}" "${branch}" | sha256sum | cut -c1-8)"
  trigger_base="${resource_name}-candidate-${normalized_branch}"
  trigger="${trigger_base:0:50}-${fingerprint}"

  branch_pattern="$(python3 - "${branch}" <<'PY'
import re, sys
print("^" + re.escape(sys.argv[1]) + "$")
PY
)"

  if ! gcloud builds repositories describe "${resource_name}"       --connection="${CONNECTION}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "ERROR: repository not linked in Cloud Build: ${repo} (${resource_name})" >&2
    exit 5
  fi

  if gcloud builds triggers describe "${trigger}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "candidate trigger exists: ${trigger}"
  else
    gcloud builds triggers create github       --name="${trigger}"       --repository="${repository}"       --branch-pattern="${branch_pattern}"       --build-config='cloudbuild.yaml'       --region="${REGION}"       --service-account="${EXECUTOR_SA}"       --project="${PROJECT_ID}"
    echo "candidate trigger created: ${trigger}"
  fi

  if [[ "${RUN_NOW}" == "true" ]]; then
    echo "running candidate gate: ${repo}@${branch}"
    gcloud builds triggers run "${trigger}"       --branch="${branch}"       --region="${REGION}"       --project="${PROJECT_ID}"
  fi
done
