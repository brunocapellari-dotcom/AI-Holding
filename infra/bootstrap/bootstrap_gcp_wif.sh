#!/usr/bin/env bash
set -euo pipefail

cat >&2 <<'EOF'
DEPRECATED: GitHub Actions Workload Identity Federation is no longer part of
the canonical AI-Holding production path.

Canonical execution:
  GitHub -> Cloud Build -> approved Cloud Build release -> GCP runtime

This script intentionally performs no IAM, WIF, deploy or infrastructure
mutation.

For shared build infrastructure use:
  scripts/bootstrap_holding_shared_gcp.sh

For the bounded production release identity use:
  infra/bootstrap/bootstrap_gcp_release_identity.sh
EOF

exit 64
