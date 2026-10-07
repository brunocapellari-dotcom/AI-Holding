from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReleaseState(StrEnum):
    TODO = "TODO"
    DOING = "DOING"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    TESTING = "TESTING"
    DONE = "DONE"


class ReleasePriority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class Workstream(StrictModel):
    project: str
    responsibility: str
    status: ReleaseState


class ReleaseTask(StrictModel):
    key: str
    project: str
    priority: ReleasePriority
    status: ReleaseState
    owner: str | None = None
    impact: str | None = None
    action_required: str | None = None
    dependency: str | None = None
    artifact: str | None = None
    test: str | None = None
    evidence: list[str] = Field(default_factory=list)
    commit_or_deploy: str | None = None

    @model_validator(mode="after")
    def done_requires_objective_evidence(self) -> ReleaseTask:
        if self.status is ReleaseState.DONE and (
            self.artifact is None or self.test is None or not self.evidence
        ):
            raise ValueError("DONE requires artifact, test and evidence")
        if self.status is ReleaseState.BLOCKED:
            required = (self.owner, self.impact, self.action_required, self.dependency)
            if any(value is None or not value.strip() for value in required):
                raise ValueError(
                    "BLOCKED requires owner, impact, action_required and dependency"
                )
        return self


class CommercialTest(StrictModel):
    question: str
    passed: bool
    evidence: list[str] = Field(default_factory=list)


class ReleaseManifest(StrictModel):
    initiative: str
    target_date: str
    product: str
    release_status: ReleaseState
    workstreams: list[Workstream]
    tasks: list[ReleaseTask]
    required_gate: list[str]
    evidence: dict[str, list[str]]
    commercial_test: CommercialTest
    rules: dict[str, Any]

    @property
    def p2_frozen(self) -> bool:
        return any(
            task.priority in {ReleasePriority.P0, ReleasePriority.P1}
            and task.status is not ReleaseState.DONE
            for task in self.tasks
        )

    @property
    def missing_gate_evidence(self) -> set[str]:
        return {
            item
            for item in self.required_gate
            if not self.evidence.get(item)
        }

    @property
    def completed(self) -> bool:
        return (
            not self.missing_gate_evidence
            and self.commercial_test.passed
            and bool(self.commercial_test.evidence)
            and all(task.status is ReleaseState.DONE for task in self.tasks)
        )

    def dashboard(self) -> list[dict[str, object]]:
        return [
            {
                "project": task.project,
                "task": task.key,
                "priority": task.priority.value,
                "status": task.status.value,
                "blocker": task.impact if task.status is ReleaseState.BLOCKED else None,
                "evidence": task.evidence,
            }
            for task in self.tasks
        ]


def load_release_manifest(path: str | Path) -> ReleaseManifest:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ReleaseManifest.model_validate(payload)
