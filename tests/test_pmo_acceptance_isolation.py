import json
from uuid import UUID

import httpx
import pytest

from app.models.agent_identity import AgentIdentity
from app.models.entities import (
    Agent,
    AgentStatus,
    AuditEvent,
    Project,
    ProjectStatus,
    Task,
    WorkStatus,
)
from app.pmo_acceptance import prepare_acceptance
from app.pmo_worker import WorkerConfig, WorkerStage, WorkerStageError, _worker_exit_code, run_once

OLD_RELEASE = "southamerica-east1-docker.pkg.dev/example/image@sha256:old"
NEW_RELEASE = "southamerica-east1-docker.pkg.dev/example/image@sha256:new"
AGENT_ID = "11111111-1111-1111-1111-111111111111"
PROJECT_ID = "22222222-2222-2222-2222-222222222222"
TASK_ID = "33333333-3333-3333-3333-333333333333"
RUN_ID = "44444444-4444-4444-4444-444444444444"


def seed_runtime(db_session):
    agent = Agent(
        key="PMO_IA",
        name="PMO IA",
        role="Portfolio execution and dependency manager",
        status=AgentStatus.disabled,
        max_autonomy=4,
    )
    project = Project(
        key="AI_HOLDING",
        name="AI Holding",
        status=ProjectStatus.active,
        priority=0,
        autonomy_level=4,
        strategic_goal="Operate the Holding safely.",
    )
    db_session.add_all([agent, project])
    db_session.flush()
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject="123456789",
            email="holding-pmo-worker@example.iam.gserviceaccount.com",
        )
    )
    db_session.commit()
    return agent, project


def test_new_acceptance_supersedes_stale_ready_acceptance(db_session):
    seed_runtime(db_session)
    old = prepare_acceptance(db_session, OLD_RELEASE)
    new = prepare_acceptance(db_session, NEW_RELEASE)

    old_task = db_session.get(Task, UUID(str(old["task_id"])))
    new_task = db_session.get(Task, UUID(str(new["task_id"])))
    assert old_task is not None
    assert new_task is not None
    assert old_task.status == WorkStatus.cancelled
    assert "superseded by production acceptance" in (old_task.blocked_reason or "")
    assert new_task.status == WorkStatus.ready
    assert new["superseded_tasks"] == 1
    assert (
        db_session.query(AuditEvent)
        .filter(AuditEvent.action == "pmo.production_acceptance.superseded")
        .count()
        == 1
    )


def test_new_acceptance_rejects_prior_running_acceptance(db_session):
    seed_runtime(db_session)
    old = prepare_acceptance(db_session, OLD_RELEASE)
    old_task = db_session.get(Task, UUID(str(old["task_id"])))
    assert old_task is not None
    old_task.status = WorkStatus.running
    db_session.commit()

    with pytest.raises(RuntimeError, match="prior production acceptance is still running"):
        prepare_acceptance(db_session, NEW_RELEASE)


def test_invalid_claim_execution_kind_fails_at_dispatch_stage():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/api/v1/pmo/claim":
            return httpx.Response(
                200,
                json={
                    "task": {
                        "id": TASK_ID,
                        "key": "INVALID_KIND",
                        "project_id": PROJECT_ID,
                        "execution_kind": "unsupported_kind",
                    },
                    "run": {
                        "id": RUN_ID,
                        "task_id": TASK_ID,
                        "agent_id": AGENT_ID,
                        "status": "queued",
                    },
                },
            )
        body = json.loads(request.content) if request.content else None
        assert body is not None
        return httpx.Response(200, json={"ok": True})

    with pytest.raises(WorkerStageError) as caught:
        run_once(
            WorkerConfig(control_plane_url="https://holding.example"),
            token_provider=lambda audience: "test-token",
            transport=httpx.MockTransport(handler),
        )

    assert caught.value.stage == WorkerStage.dispatch
    assert _worker_exit_code(caught.value) == 48
