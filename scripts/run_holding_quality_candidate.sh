#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
TRIGGER="${QUALITY_TRIGGER:-ai-holding-quality-manual}"
SHA="${1:-}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure PROJECT_ID or gcloud project first" >&2
  exit 2
fi
if [[ -z "${SHA}" ]]; then
  echo "usage: $0 <COMMIT_SHA>" >&2
  exit 2
fi

BUILD_ID="$(
  gcloud builds triggers run "${TRIGGER}"     --region="${REGION}"     --project="${PROJECT_ID}"     --sha="${SHA}"     --format='value(metadata.build.id)'
)"

if [[ -z "${BUILD_ID}" ]]; then
  echo "ERROR: Cloud Build did not return a build id" >&2
  exit 3
fi

echo "quality build id: ${BUILD_ID}"
gcloud builds log --stream "${BUILD_ID}"   --region="${REGION}"   --project="${PROJECT_ID}" || true

STATUS="$(
  gcloud builds describe "${BUILD_ID}"     --region="${REGION}"     --project="${PROJECT_ID}"     --format='value(status)'
)"

if [[ "${STATUS}" != "SUCCESS" ]]; then
  echo "quality gate failed: ${STATUS}" >&2
  exit 4
fi

IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/ai-execution/ai-holding:${BUILD_ID}"
IMAGE_REF="$(
  gcloud artifacts docker images describe "${IMAGE_TAG}"     --project="${PROJECT_ID}"     --format='value(image_summary.fully_qualified_digest)'
)"
test -n "${IMAGE_REF}"

gcloud artifacts docker images describe "${IMAGE_REF}"   --project="${PROJECT_ID}"   --show-provenance   --format=json > "/tmp/ai-holding-${BUILD_ID}-provenance.json"

python3 - "/tmp/ai-holding-${BUILD_ID}-provenance.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
provenance = ((data.get("provenance_summary") or {}).get("provenance") or [])
if not provenance:
    raise SystemExit("candidate has no verified Cloud Build provenance")
PY

cat <<EOF

QUALITY GATE PASSED
commit: ${SHA}
build:  ${BUILD_ID}
image:  ${IMAGE_REF}

Production remains separate. To request promotion:
gcloud builds triggers run ai-holding-release-manual \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --sha=${SHA} \
  --substitutions=_CANDIDATE_BUILD_ID=${BUILD_ID},_SOURCE_COMMIT_SHA=${SHA}

The release trigger still requires explicit Cloud Build approval before production execution.
EOF
