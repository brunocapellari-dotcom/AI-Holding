from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.bootstrap import bootstrap_canonical_portfolio
from app.core.actor import ActorContext
from app.models.entities import Agent, AgentStatus, Project, ProjectStatus, Task, WorkStatus
from app.models.routine import Routine
from app.services.pmo import claim_next_task
from app.services.routines import materialize_due_routines

ACTOR = ActorContext(name="test-pmo", actor_type="agent", authenticated=True)
SUPPORTED_KINDS = ("control_plane_health",)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def canonical_entities(db_session):
    bootstrap_canonical_portfolio(db_session)
    pmo = db_session.scalar(select(Agent).where(Agent.key == "PMO_IA"))
    holding = db_session.scalar(select(Project).where(Project.key == "AI_HOLDING"))
    routine = db_session.scalar(select(Routine).where(Routine.key == "CONTROL_PLANE_HEALTH"))
    assert pmo is not None
    assert holding is not None
    assert routine is not None
    return pmo, holding, routine


def test_due_routine_materializes_one_task_and_skips_stale_intervals(db_session):
    pmo, holding, routine = canonical_entities(db_session)
    scheduled_for = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    now = scheduled_for + timedelta(minutes=25)
    routine.next_due_at = scheduled_for
    db_session.commit()

    created = materialize_due_routines(
        db_session,
        actor=ACTOR,
        execution_kinds=SUPPORTED_KINDS,
        now=now,
    )
    db_session.commit()

    assert len(created) == 1
    task = db_session.get(Task, created[0])
    assert task is not None
    assert task.project_id == holding.id
    assert task.assigned_agent_id == pmo.id
    assert task.execution_kind == "control_plane_health"
    assert task.auto_start is True
    assert task.status == WorkStatus.planned
    assert task.due_at is not None
    assert as_utc(task.due_at) == scheduled_for
    assert task.metadata_json["routine_id"] == str(routine.id)
    assert task.metadata_json["scheduled_for"] == scheduled_for.isoformat()
    assert task.metadata_json["skipped_intervals"] == 2
    assert as_utc(routine.next_due_at) == scheduled_for + timedelta(minutes=30)

    second = materialize_due_routines(
        db_session,
        actor=ACTOR,
        execution_kinds=SUPPORTED_KINDS,
        now=now,
    )
    assert second == []


def test_claim_cycle_materializes_promotes_and_claims_due_routine(db_session):
    pmo, _, routine = canonical_entities(db_session)
    pmo.status = AgentStatus.active
    routine.next_due_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.commit()

    claimed = claim_next_task(
        db_session,
        agent=pmo,
        actor=ACTOR,
        execution_kinds=SUPPORTED_KINDS,
    )
    assert claimed is not None
    task, run = claimed
    assert task.execution_kind == "control_plane_health"
    assert task.auto_start is True
    assert task.status == WorkStatus.running
    assert task.metadata_json["routine_id"] == str(routine.id)
    assert run.task_id == task.id
    assert run.input_metadata["claim_source"] == "pmo"


def test_disabled_routine_and_paused_project_do_not_materialize(db_session):
    _, holding, routine = canonical_entities(db_session)
    now = datetime.now(UTC)
    routine.next_due_at = now - timedelta(minutes=1)
    routine.enabled = False
    db_session.commit()

    assert (
        materialize_due_routines(
            db_session,
            actor=ACTOR,
            execution_kinds=SUPPORTED_KINDS,
            now=now,
        )
        == []
    )

    routine.enabled = True
    holding.status = ProjectStatus.paused
    db_session.commit()
    assert (
        materialize_due_routines(
            db_session,
            actor=ACTOR,
            execution_kinds=SUPPORTED_KINDS,
            now=now,
        )
        == []
    )


def test_routine_materialization_respects_execution_kind_filter(db_session):
    _, _, routine = canonical_entities(db_session)
    now = datetime.now(UTC)
    routine.next_due_at = now - timedelta(minutes=1)
    db_session.commit()

    created = materialize_due_routines(
        db_session,
        actor=ACTOR,
        execution_kinds=("unsupported-kind",),
        now=now,
    )
    assert created == []
