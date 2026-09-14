from uuid import UUID

import pytest

from app.knowledge_acceptance import (
    acceptance_context,
    finalize_acceptance,
    prepare_acceptance,
)
from app.models.agent_identity import AgentIdentity
from app.models.entities import (
    Agent,
    AgentStatus,
    AuditEvent,
    Incident,
    IncidentStatus,
    Project,
    ProjectStatus,
    Run,
    RunStatus,
    Severity,
    Task,
    WorkStatus,
)

RELEASE_ID = "southamerica-east1-docker.pkg.dev/example/image@sha256:knowledge123"


def seed_canonical_runtime(db_session):
    agent = Agent(
        key="KNOWLEDGE_IA",
        name="Knowledge IA",
        role="Universal knowledge ingestion and memory steward for all projects",
        status=AgentStatus.disabled,
        max_autonomy=4,
    )
    project = Project(
        key="SECOND_BRAIN",
        name="Segundo Cérebro Universal",
        status=ProjectStatus.active,
        priority=0,
        autonomy_level=4,
        strategic_goal="Operate universal shared knowledge safely.",
    )
    db_session.add_all([agent, project])
    db_session.flush()
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject="987654321",
            email="holding-knowledge-worker@example.iam.gserviceaccount.com",
        )
    )
    db_session.commit()
    return agent, project


def test_prepare_is_idempotent_and_activates_only_canonical_knowledge_agent(db_session):
    agent, project = seed_canonical_runtime(db_session)

    first = prepare_acceptance(db_session, RELEASE_ID)
    second = prepare_acceptance(db_session, RELEASE_ID)

    context = acceptance_context(RELEASE_ID)
    tasks = db_session.query(Task).filter(Task.idempotency_key == context.idempotency_key).all()
    assert len(tasks) == 1
    task = tasks[0]
    assert first["task_id"] == second["task_id"] == str(task.id)
    assert task.project_id == project.id
    assert task.assigned_agent_id == agent.id
    assert task.execution_kind == "knowledge_gap_scan"
    assert task.status == WorkStatus.ready
    assert agent.status == AgentStatus.active


def test_finalize_requires_succeeded_run_and_structured_read_only_output(db_session):
    agent, _ = seed_canonical_runtime(db_session)
    prepared = prepare_acceptance(db_session, RELEASE_ID)
    task = db_session.get(Task, UUID(str(prepared["task_id"])))
    assert task is not None
    task.status = WorkStatus.review
    run = Run(
        task_id=task.id,
        agent_id=agent.id,
        status=RunStatus.succeeded,
        attempt=1,
        output_metadata={
            "execution_kind": "knowledge_gap_scan",
            "candidate_count": 2,
            "claim_ids": [
                "11111111-1111-1111-1111-111111111111",
                "22222222-2222-2222-2222-222222222222",
            ],
        },
    )
    db_session.add(run)
    db_session.commit()

    result = finalize_acceptance(db_session, RELEASE_ID)

    assert result["task_status"] == "done"
    assert result["run_status"] == "succeeded"
    assert result["agent_status"] == "active"
    assert task.status == WorkStatus.done
    audits = db_session.query(AuditEvent).filter(
        AuditEvent.action == "knowledge.production_acceptance.verified"
    )
    assert audits.count() == 1


def test_finalize_fails_closed_and_disables_agent_on_bad_output(db_session):
    agent, _ = seed_canonical_runtime(db_session)
    prepared = prepare_acceptance(db_session, RELEASE_ID)
    task = db_session.get(Task, UUID(str(prepared["task_id"])))
    assert task is not None
    task.status = WorkStatus.review
    db_session.add(
        Run(
            task_id=task.id,
            agent_id=agent.id,
            status=RunStatus.succeeded,
            attempt=1,
            output_metadata={
                "execution_kind": "knowledge_gap_scan",
                "candidate_count": 2,
                "claim_ids": ["only-one-id"],
            },
        )
    )
    db_session.commit()

    with pytest.raises(RuntimeError, match="does not match"):
        finalize_acceptance(db_session, RELEASE_ID)

    assert agent.status == AgentStatus.disabled
    failed = db_session.query(AuditEvent).filter(
        AuditEvent.action == "knowledge.production_acceptance.failed"
    )
    assert failed.count() == 1


def test_finalize_rejects_any_unresolved_worker_incident_for_acceptance_task(db_session):
    agent, project = seed_canonical_runtime(db_session)
    prepared = prepare_acceptance(db_session, RELEASE_ID)
    task = db_session.get(Task, UUID(str(prepared["task_id"])))
    assert task is not None
    task.status = WorkStatus.review
    db_session.add_all(
        [
            Run(
                task_id=task.id,
                agent_id=agent.id,
                status=RunStatus.succeeded,
                attempt=1,
                output_metadata={
                    "execution_kind": "knowledge_gap_scan",
                    "candidate_count": 0,
                    "claim_ids": [],
                },
            ),
            Incident(
                project_id=project.id,
                severity=Severity.sev3,
                title="Worker incident",
                status=IncidentStatus.open,
                source="pmo-worker",
                details={"task_id": str(task.id)},
            ),
        ]
    )
    db_session.commit()

    with pytest.raises(RuntimeError, match="unresolved worker incident"):
        finalize_acceptance(db_session, RELEASE_ID)

    assert agent.status == AgentStatus.disabled


def test_prepare_fails_closed_without_runtime_identity(db_session):
    agent = Agent(
        key="KNOWLEDGE_IA",
        name="Knowledge IA",
        role="Knowledge",
        status=AgentStatus.disabled,
        max_autonomy=4,
    )
    project = Project(
        key="SECOND_BRAIN",
        name="Segundo Cérebro Universal",
        status=ProjectStatus.active,
        priority=0,
        autonomy_level=4,
        strategic_goal="Operate safely.",
    )
    db_session.add_all([agent, project])
    db_session.commit()

    with pytest.raises(RuntimeError, match="runtime identity binding"):
        prepare_acceptance(db_session, RELEASE_ID)
