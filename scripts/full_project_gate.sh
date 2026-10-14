#!/usr/bin/env bash
set -euo pipefail

python -m compileall -q app tests alembic
python -m pip check

ruff check app tests alembic
ruff format --check app tests alembic
mypy app
pip-audit
bandit -c pyproject.toml -r app
semgrep scan --config .semgrep.yml --error --metrics=off app
# GitHub Actions was removed (Cloud Build is the canonical runner). zizmor
# exits 3 when there is nothing to collect, so audit strictly whenever any
# GitHub workflow/action/dependabot file is (re)introduced.
if [[ -n "$(find . -path ./.git -prune -o \( -path './.github/*' -o -name 'action.yml' -o -name 'action.yaml' \) -type f -print -quit)" ]]; then
  zizmor --strict-collection --collect=workflows,actions,dependabot .
else
  echo "zizmor: no GitHub workflows, actions or dependabot config to audit"
fi

runtime_license_root="$(mktemp -d)"
trap 'rm -rf "${runtime_license_root}"' EXIT
runtime_license_venv="${runtime_license_root}/runtime-license"
runtime_license_json="${runtime_license_root}/runtime-licenses.json"

python -m venv "${runtime_license_venv}"
"${runtime_license_venv}/bin/pip" install --disable-pip-version-check --quiet . pip-licenses
"${runtime_license_venv}/bin/pip-licenses" --from=all --format=json > "${runtime_license_json}"

python - "${runtime_license_json}" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
packages = json.loads(report_path.read_text(encoding="utf-8"))

blocked_patterns = (
    re.compile(r"\bGNU Affero General Public License\b", re.IGNORECASE),
    re.compile(r"\bGNU General Public License\b", re.IGNORECASE),
    re.compile(r"\bServer Side Public License\b", re.IGNORECASE),
    re.compile(r"\bAGPL(?:[-_ .]?v?\d|\b)", re.IGNORECASE),
    re.compile(r"\bSSPL(?:[-_ .]?v?\d|\b)", re.IGNORECASE),
    # Word boundary prevents matching LGPL-* while still catching GPL-*.
    re.compile(r"\bGPL(?:[-_ .]?v?\d|\b)", re.IGNORECASE),
)

violations: list[str] = []
unknown: list[str] = []
for package in packages:
    name = str(package.get("Name", "<unknown>"))
    version = str(package.get("Version", "<unknown>"))
    license_text = str(package.get("License", "")).strip()
    if not license_text or license_text.upper() == "UNKNOWN":
        unknown.append(f"{name}=={version}")
        continue
    if any(pattern.search(license_text) for pattern in blocked_patterns):
        violations.append(f"{name}=={version}: {license_text}")

if unknown:
    print(
        "License metadata requiring manual review (non-blocking until policy is expanded): "
        + ", ".join(sorted(unknown)),
        file=sys.stderr,
    )

if violations:
    print("Blocked strong-copyleft/server-side licenses detected:", file=sys.stderr)
    for violation in sorted(violations):
        print(f"  - {violation}", file=sys.stderr)
    raise SystemExit(1)
PY

alembic upgrade head
alembic check
alembic downgrade base
alembic upgrade head
alembic check
pytest

terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate

docker build --pull --tag holding-control-plane:ci .
docker run --rm holding-control-plane:ci python -c \
  "import app.main, app.db_migrate, app.bootstrap, app.pmo_worker, app.github_collector, app.pmo_acceptance, app.knowledge_acceptance"
