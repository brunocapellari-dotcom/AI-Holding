from __future__ import annotations

import pytest

from scripts import verify_local_handoff as handoff


def test_local_handoff_matches_real_receipt(monkeypatch) -> None:
    def fake_get(base: str, path: str):
        assert base in {"http://127.0.0.1:8080", "http://127.0.0.1:8001"}
        if path == "/ready":
            return {"status": "ready"}
        if path == "/v1/operational/health":
            return {"status": "healthy", "workers_healthy": 1}
        if path.startswith("/api/v1/holding/control-plane/event-feed"):
            return {
                "availability_verified": False,
                "items": [
                    {"event_id": "real-event-0001", "project_key": "AGROLOG_MT"},
                    {"event_id": "other-event-0002", "project_key": "RESEARCH_AI"},
                ],
            }
        raise AssertionError(path)

    monkeypatch.setattr(handoff, "_json_get", fake_get)
    report = handoff.verify_handoff(
        "http://127.0.0.1:8080", "http://127.0.0.1:8001", "real-event-0001", "AGROLOG_MT"
    )
    assert report["status"] == "PASS"
    assert report["holding_persisted_matching_receipts"] == 1
    assert (
        handoff.verify_handoff(
            "http://127.0.0.1:8080", "http://127.0.0.1:8001", "missing-evt-0000", "AGROLOG_MT"
        )["status"]
        == "BLOCKED"
    )


def test_unhealthy_worker_blocks_real_handoff(monkeypatch) -> None:
    def fake_get(base: str, path: str):
        if path == "/ready":
            return {"status": "ready"}
        return {"workers_healthy": 0}

    monkeypatch.setattr(handoff, "_json_get", fake_get)
    with pytest.raises(RuntimeError, match="healthy"):
        handoff.verify_handoff(
            "http://127.0.0.1:8080", "http://127.0.0.1:8001", "real-event-0001", "AGROLOG_MT"
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://192.168.0.1:8080",
        "http://169.254.169.254:80",
        "http://127.0.0.1:8080/path",
        "http://user:pass@127.0.0.1:8080",
        "http://localhost:8080/#fragment",
    ],
)
def test_remote_or_unsafe_endpoints_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        handoff._local_base(url)
