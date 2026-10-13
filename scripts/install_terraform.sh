#!/usr/bin/env bash
set -euo pipefail

VERSION="${TERRAFORM_VERSION:-1.9.8}"
DEST="${1:-/workspace/.bin}"
mkdir -p "${DEST}"
ZIP="/tmp/terraform_${VERSION}.zip"
SUMS="/tmp/terraform_${VERSION}_SHA256SUMS"

curl -fsSLo "${ZIP}" "https://releases.hashicorp.com/terraform/${VERSION}/terraform_${VERSION}_linux_amd64.zip"
curl -fsSLo "${SUMS}" "https://releases.hashicorp.com/terraform/${VERSION}/terraform_${VERSION}_SHA256SUMS"

(
  cd /tmp
  grep " terraform_${VERSION}_linux_amd64.zip$" "${SUMS}" > terraform.sha256
  sha256sum -c terraform.sha256
)

python3 - "${ZIP}" "${DEST}" <<'PY'
import sys
import zipfile

archive, dest = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(archive) as zf:
    member = zf.getinfo("terraform")
    zf.extract(member, dest)
PY

chmod +x "${DEST}/terraform"
"${DEST}/terraform" version
