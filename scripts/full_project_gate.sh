#!/usr/bin/env bash
set -euo pipefail

ruff check app tests alembic
ruff format --check app tests alembic
mypy app
pip-audit
bandit -c pyproject.toml -r app
semgrep scan --config .semgrep.yml --error --metrics=off app
zizmor --collect=workflows .

runtime_license_venv="$(mktemp -d)/runtime-license"
python -m venv "${runtime_license_venv}"
"${runtime_license_venv}/bin/pip" install --disable-pip-version-check --quiet . pip-licenses
"${runtime_license_venv}/bin/pip-licenses" \
  --partial-match \
  --fail-on='GNU General Public License;GNU Affero General Public License;Server Side Public License'

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
  "import app.main, app.db_migrate, app.bootstrap, app.pmo_worker, app.pmo_acceptance, app.knowledge_acceptance"
