import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.release_control import (
    ReleaseManifest,
    ReleaseState,
    ReleaseTask,
    load_release_manifest,
)

MANIFEST = Path("config/agrolog_commercial_release_2026_10_09.json")


def test_agrolog_commercial_release_manifest_is_loadable() -> None:
    release = load_release_manifest(MANIFEST)
    assert release.initiative == "AGROLOG_COMMERCIAL_RELEASE_2026_10_09"
    assert {item.project for item in release.workstreams} == {
        "AGROLOG",
        "WHATSAPP_AI",
        "RESEARCH_AI",
        "SECOND_BRAIN",
        "HERMES_AI",
    }
    assert release.p2_frozen is True
    assert release.completed is False
    assert release.missing_gate_evidence == set(release.required_gate)
    assert len(release.dashboard()) == len(release.tasks)


def test_done_requires_artifact_test_and_evidence() -> None:
    with pytest.raises(ValidationError):
        ReleaseTask(
            key="P0_REPORT",
            project="AGROLOG",
            priority="P0",
            status=ReleaseState.DONE,
        )


def test_blocked_requires_owner_impact_action_and_dependency() -> None:
    with pytest.raises(ValidationError):
        ReleaseTask(
            key="P0_SOURCE",
            project="RESEARCH_AI",
            priority="P0",
            status=ReleaseState.BLOCKED,
            owner="research-ai",
        )


def test_release_completes_only_with_all_gate_evidence_and_commercial_test() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for task in payload["tasks"]:
        task["status"] = "DONE"
        task["artifact"] = f"artifact://{task['key']}"
        task["test"] = f"test://{task['key']}"
        task["evidence"] = [f"evidence://{task['key']}"]
    payload["evidence"] = {key: [f"evidence://gate/{key}"] for key in payload["required_gate"]}
    payload["commercial_test"]["passed"] = True
    payload["commercial_test"]["evidence"] = ["evidence://commercial-test"]
    release = ReleaseManifest.model_validate(payload)
    assert release.completed is True
    assert release.p2_frozen is False


def test_release_dashboard_is_exposed_by_control_plane(client) -> None:
    response = client.get("/api/v1/executive/releases/agrolog-commercial-2026-10-09")
    assert response.status_code == 200
    payload = response.json()
    assert payload["initiative"] == "AGROLOG_COMMERCIAL_RELEASE_2026_10_09"
    assert payload["completed"] is False
    assert payload["p2_frozen"] is True
    assert "e2e" in payload["missing_gate_evidence"]
    freight = next(item for item in payload["dashboard"] if item["task"] == "P0_FRETES")
    assert freight["status"] == "TESTING"
    assert freight["last_test"] == "Both contract-side PR gates are green."
    assert freight["next_task"]
