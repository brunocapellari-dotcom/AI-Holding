"""Runner-independent local E2E receipt check for Hermes -> Holding.

Read-only: requires the event_id from a REAL Hermes execution. It does not
fabricate work, create an event, authenticate as another agent, or change state.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect not permitted in local handoff verifier")


def _local_base(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.port is None
    ):
        raise ValueError("only explicit local loopback HTTP service origins are accepted")
    return value.rstrip("/")


def _json_get(base: str, path: str) -> dict | list:
    url = _local_base(base) + path
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(request, timeout=8) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected service status: {response.status}")
        if response.headers.get_content_type() != "application/json":
            raise ValueError("unexpected response content type")
        payload = response.read(1024 * 1024 + 1)
        if len(payload) > 1024 * 1024:
            raise ValueError("response too large")
        return json.loads(payload)


def verify_handoff(
    hermes_url: str,
    holding_url: str,
    event_id: str,
    project_key: str,
) -> dict[str, object]:
    if not (8 <= len(event_id) <= 128 and 1 <= len(project_key) <= 120):
        raise ValueError("event_id or project_key invalid")
    # Ensure both origins are validated BEFORE any I/O.
    hermes = _local_base(hermes_url)
    holding = _local_base(holding_url)
    hermes_ready = _json_get(hermes, "/ready")
    holding_ready = _json_get(holding, "/ready")
    operational = _json_get(hermes, "/v1/operational/health")
    if not isinstance(hermes_ready, dict) or hermes_ready.get("status") != "ready":
        raise RuntimeError("Hermes readiness gate did not pass")
    if not isinstance(holding_ready, dict) or holding_ready.get("status") != "ready":
        raise RuntimeError("Holding readiness gate did not pass")
    if not isinstance(operational, dict) or operational.get("workers_healthy", 0) < 1:
        raise RuntimeError("Hermes has no healthy operational worker")
    feed = _json_get(holding, "/api/v1/holding/control-plane/event-feed?limit=100")
    if not isinstance(feed, dict) or feed.get("availability_verified") is not False:
        raise RuntimeError("Holding feed evidence contract mismatch")
    items = feed.get("items")
    if not isinstance(items, list):
        raise RuntimeError("Holding feed returned invalid items")
    matched = [
        item for item in items
        if isinstance(item, dict)
        and item.get("event_id") == event_id
        and item.get("project_key") == project_key
    ]
    return {
        "status": "PASS" if len(matched) == 1 else "BLOCKED",
        "contract": "HERMES_TO_HOLDING_REAL_RECEIPT_V1",
        "event_id": event_id,
        "project_key": project_key,
        "hermes_worker_healthy": True,
        "holding_persisted_matching_receipts": len(matched),
        "note": "Confirms received event evidence, not full autonomous end-to-end workflows.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a real Hermes event reached Holding")
    parser.add_argument("--hermes", default="http://127.0.0.1:8080")
    parser.add_argument("--holding", default="http://127.0.0.1:8001")
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--project-key", required=True)
    args = parser.parse_args()
    try:
        report = verify_handoff(args.hermes, args.holding, args.event_id, args.project_key)
    except (ValueError, RuntimeError, OSError, urllib.error.URLError) as exc:
        report = {"status": "BLOCKED", "reason": type(exc).__name__}
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 3


if __name__ == "__main__":
    sys.exit(main())
