#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${MANIFEST:-${ROOT_DIR}/infra/gcp/ecosystem-projects.json}"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
CONNECTION="${GCP_GITHUB_CONNECTION:-ai-github}"
EXECUTOR_SA_NAME="${EXECUTOR_SA_NAME:-ai-build-executor}"
EXECUTOR_SA="projects/${PROJECT_ID}/serviceAccounts/${EXECUTOR_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
CANDIDATE_REPO="${1:-${CANDIDATE_REPO:-}}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure PROJECT_ID or the active gcloud project first" >&2
  exit 2
fi

if [[ -z "${CANDIDATE_REPO}" ]]; then
  echo "usage: $0 <repository-name>" >&2
  exit 3
fi

for cmd in gcloud python3 sha256sum; do
  command -v "${cmd}" >/dev/null || {
    echo "ERROR: required command missing: ${cmd}" >&2
    exit 4
  }
done

readarray -t CONFIG < <(python3 - "${MANIFEST}" "${CANDIDATE_REPO}" <<'PY'
import json
import sys

manifest_path, wanted = sys.argv[1], sys.argv[2]
with open(manifest_path, encoding="utf-8") as fh:
    data = json.load(fh)

matches = [item for item in data["projects"] if item["repo"] == wanted]
if len(matches) != 1:
    raise SystemExit(f"repository_not_unique_or_missing:{wanted}")

branch = matches[0].get("candidate_branch")
if not branch:
    raise SystemExit(f"candidate_branch_not_configured:{wanted}")

print(matches[0]["repo"])
print(branch)
PY
)

REPO="${CONFIG[0]}"
BRANCH="${CONFIG[1]}"
RESOURCE_NAME="$(tr '[:upper:]_' '[:lower:]-' <<<"${REPO}" | tr -cd 'a-z0-9-')"
REPOSITORY="projects/${PROJECT_ID}/locations/${REGION}/connections/${CONNECTION}/repositories/${RESOURCE_NAME}"

NORMALIZED_BRANCH="$(tr '/[:upper:]_' '-[:lower:]-' <<<"${BRANCH}" | tr -cd 'a-z0-9-')"
FINGERPRINT="$(printf '%s:%s' "${REPO}" "${BRANCH}" | sha256sum | cut -c1-8)"
TRIGGER_BASE="${RESOURCE_NAME}-candidate-${NORMALIZED_BRANCH}"
TRIGGER="${TRIGGER_BASE:0:50}-${FINGERPRINT}"

BRANCH_PATTERN="$(python3 - "${BRANCH}" <<'PY'
import re
import sys

print("^" + re.escape(sys.argv[1]) + "$")
PY
)"

echo "== verify Cloud Build repository link =="
gcloud builds repositories describe "${RESOURCE_NAME}"   --connection="${CONNECTION}"   --region="${REGION}"   --project="${PROJECT_ID}" >/dev/null

echo "== ensure exact candidate trigger =="
if ! gcloud builds triggers describe "${TRIGGER}"     --region="${REGION}"     --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud builds triggers create github     --name="${TRIGGER}"     --repository="${REPOSITORY}"     --branch-pattern="${BRANCH_PATTERN}"     --build-config='cloudbuild.yaml'     --region="${REGION}"     --service-account="${EXECUTOR_SA}"     --project="${PROJECT_ID}"
fi

echo "== run ${REPO}@${BRANCH} candidate =="
BUILD_ID="$(gcloud builds triggers run "${TRIGGER}"   --branch="${BRANCH}"   --region="${REGION}"   --project="${PROJECT_ID}"   --format='value(metadata.build.id)')"

if [[ -z "${BUILD_ID}" ]]; then
  echo "ERROR: Cloud Build did not return a build id" >&2
  exit 5
fi

echo "BUILD_ID=${BUILD_ID}"
echo "TRIGGER=${TRIGGER}"
echo "REPOSITORY=${REPO}"
echo "BRANCH=${BRANCH}"

if [[ "${STREAM_LOGS:-true}" == "true" ]]; then
  set +e
  gcloud builds log --stream "${BUILD_ID}"     --region="${REGION}"     --project="${PROJECT_ID}"
  LOG_STATUS=$?
  set -e
  if [[ "${LOG_STATUS}" -ne 0 ]]; then
    echo "Cloud Build log stream ended non-zero; checking final build state." >&2
  fi
fi

STATUS="$(gcloud builds describe "${BUILD_ID}"   --region="${REGION}"   --project="${PROJECT_ID}"   --format='value(status)')"

echo "STATUS=${STATUS}"

case "${STATUS}" in
  SUCCESS)
    echo "Candidate gate PASS: ${REPO}@${BRANCH}"
    ;;
  FAILURE)
    echo "Candidate gate completed with FAILURE. Inspect the failing Cloud Build step and persisted evidence." >&2
    exit 10
    ;;
  CANCELLED|TIMEOUT|EXPIRED)
    echo "Candidate gate did not complete successfully: ${STATUS}" >&2
    exit 11
    ;;
  *)
    echo "Candidate gate ended in unexpected state: ${STATUS}" >&2
    exit 12
    ;;
esac
