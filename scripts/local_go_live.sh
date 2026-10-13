#!/usr/bin/env bash
set -euo pipefail

command -v docker >/dev/null 2>&1 || {
  echo "Docker is required for the zero-cost local runtime." >&2
  exit 2
}

docker compose version >/dev/null
docker compose up --build -d

for attempt in $(seq 1 36); do
  if curl --fail --silent --show-error http://127.0.0.1:8080/ready >/dev/null 2>&1; then
    curl --fail --silent --show-error http://127.0.0.1:8080/health
    printf '\nHolding owner console: http://127.0.0.1:8080/\n'
    docker compose ps
    exit 0
  fi
  sleep 5
done

echo "Holding did not become ready. Recent logs:" >&2
docker compose logs --tail=120 api pmo-worker knowledge-worker >&2
exit 3
