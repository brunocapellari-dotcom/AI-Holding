#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANIFEST="${ROOT_DIR}/infra/gcp/ecosystem-projects.json"
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-southamerica-east1}"
CONNECTION="${GCP_GITHUB_CONNECTION:-ai-github}"
EXECUTOR_SA_NAME="${EXECUTOR_SA_NAME:-ai-build-executor}"
EXECUTOR_SA="${EXECUTOR_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
RELEASE_SA_NAME="${RELEASE_SA_NAME:-github-deployer}"
RELEASE_SA="${RELEASE_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
AR_REPO="${AR_REPO:-ai-execution}"
EVIDENCE_BUCKET="${EVIDENCE_BUCKET:-${PROJECT_ID}-ai-execution-evidence}"
GITHUB_OWNER="${GITHUB_OWNER:-brunocapellari-dotcom}"

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "ERROR: configure o projeto: gcloud config set project <PROJECT_ID>" >&2
  exit 2
fi
if [[ ! -f "${MANIFEST}" ]]; then
  echo "ERROR: manifest ausente: ${MANIFEST}" >&2
  exit 3
fi

for cmd in gcloud python3; do
  command -v "${cmd}" >/dev/null || { echo "ERROR: ${cmd} nao encontrado" >&2; exit 4; }
done

echo "== GCP execution fabric =="
echo "project=${PROJECT_ID}"
echo "region=${REGION}"
echo "connection=${CONNECTION}"

gcloud services enable \
  cloudbuild.googleapis.com \
  containeranalysis.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudscheduler.googleapis.com \
  pubsub.googleapis.com \
  sqladmin.googleapis.com \
  bigquery.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  iamcredentials.googleapis.com \
  serviceusage.googleapis.com \
  --project="${PROJECT_ID}"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
CB_AGENT="service-${PROJECT_NUMBER}@gcp-sa-cloudbuild.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "${EXECUTOR_SA}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${EXECUTOR_SA_NAME}" \
    --display-name="AI ecosystem Cloud Build executor" \
    --project="${PROJECT_ID}"
fi

# Scope Cloud Build's service-agent impersonation to the designated executor only.
gcloud iam service-accounts add-iam-policy-binding "${EXECUTOR_SA}" \
  --member="serviceAccount:${CB_AGENT}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --project="${PROJECT_ID}" \
  --quiet >/dev/null

for role in roles/logging.logWriter roles/artifactregistry.writer roles/storage.objectViewer; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${EXECUTOR_SA}" \
    --role="${role}" \
    --condition=None \
    --quiet >/dev/null
 done

# User-specified Cloud Build identities need this self-binding to mint short-lived
# OIDC identity tokens for Sigstore/Cosign release signing. No static signing key is created.
gcloud iam service-accounts add-iam-policy-binding "${EXECUTOR_SA}" \
  --member="serviceAccount:${EXECUTOR_SA}" \
  --role="roles/iam.serviceAccountOpenIdTokenCreator" \
  --project="${PROJECT_ID}" \
  --quiet >/dev/null

if ! gcloud artifacts repositories describe "${AR_REPO}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Canonical container registry for the AI ecosystem" \
    --project="${PROJECT_ID}"
fi

if ! gcloud storage buckets describe "gs://${EVIDENCE_BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${EVIDENCE_BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
fi

gcloud storage buckets add-iam-policy-binding "gs://${EVIDENCE_BUCKET}" \
  --member="serviceAccount:${EXECUTOR_SA}" \
  --role="roles/storage.objectAdmin" >/dev/null

# Reuse the existing bounded production deployer as the Cloud Build release identity.
# Do not create a second production authority in parallel.
if gcloud iam service-accounts describe "${RELEASE_SA}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud iam service-accounts add-iam-policy-binding "${RELEASE_SA}" \
    --member="serviceAccount:${CB_AGENT}" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project="${PROJECT_ID}" \
    --quiet >/dev/null
  gcloud iam service-accounts add-iam-policy-binding "${RELEASE_SA}" \
    --member="serviceAccount:${RELEASE_SA}" \
    --role="roles/iam.serviceAccountOpenIdTokenCreator" \
    --project="${PROJECT_ID}" \
    --quiet >/dev/null
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RELEASE_SA}" \
    --role="roles/logging.logWriter" \
    --condition=None \
    --quiet >/dev/null
  gcloud storage buckets add-iam-policy-binding "gs://${EVIDENCE_BUCKET}" \
    --member="serviceAccount:${RELEASE_SA}" \
    --role="roles/storage.objectAdmin" >/dev/null
else
  echo "release service account not present yet: ${RELEASE_SA}; production promotion remains disabled"
fi

if ! gcloud builds connections describe "${CONNECTION}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Criando conexao Cloud Build <-> GitHub. O comando exibira um link de autorizacao no navegador."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${CB_AGENT}" \
    --role="roles/secretmanager.admin" \
    --condition=None \
    --quiet >/dev/null
  gcloud builds connections create github "${CONNECTION}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" || true
fi

CONNECTION_JSON="$(gcloud builds connections describe "${CONNECTION}" --region="${REGION}" --project="${PROJECT_ID}" --format=json)"
STATE="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("installationState") or {}).get("stage", "UNKNOWN"))' <<<"${CONNECTION_JSON}")"
ACTION_URI="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("installationState") or {}).get("actionUri", ""))' <<<"${CONNECTION_JSON}")"

if [[ "${STATE}" != "COMPLETE" ]]; then
  echo
  echo "BLOQUEIO HUMANO UNICO: autorize o GitHub App do Cloud Build."
  [[ -n "${ACTION_URI}" ]] && echo "Abra: ${ACTION_URI}"
  echo "Depois execute este mesmo script novamente."
  exit 20
fi

# The broad Secret Manager Admin role is only needed to bootstrap the connection.
gcloud projects remove-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CB_AGENT}" \
  --role="roles/secretmanager.admin" \
  --condition=None \
  --quiet >/dev/null 2>&1 || true

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
  if gcloud builds repositories describe "${resource_name}" \
      --connection="${CONNECTION}" --region="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "repository linked: ${repo}"
    continue
  fi
  gcloud builds repositories create "${resource_name}" \
    --remote-uri="https://github.com/${GITHUB_OWNER}/${repo}.git" \
    --connection="${CONNECTION}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}"
done

cat <<EOF

BASE GCP EXECUTION FABRIC: READY
- Project: ${PROJECT_ID}
- Region: ${REGION}
- GitHub connection: ${CONNECTION}
- Build service account: ${EXECUTOR_SA}
- Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}
- Evidence bucket: gs://${EVIDENCE_BUCKET}
- Linked repositories: ${#REPOS[@]}

Next: merge each repository's cloudbuild.yaml and then run scripts/activate_gcp_build_triggers.sh.
EOF
