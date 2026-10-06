import pytest
from sqlalchemy import select

from app.bootstrap import (
    AGENT_SEEDS,
    PROJECT_SEEDS,
    ROUTINE_SEEDS,
    RuntimeIdentitySeed,
    _runtime_identity_seeds_from_env,
    bootstrap_canonical_portfolio,
    bootstrap_owner_identity,
)
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus, Project, ProjectStatus
from app.models.human_identity import HumanIdentityRole, HumanRole
from app.models.routine import Routine


def test_canonical_bootstrap_is_idempotent_and_preserves_runtime_state(db_session):
    first = bootstrap_canonical_portfolio(db_session)
    assert first == {
        "created_agents": len(AGENT_SEEDS),
        "created_projects": len(PROJECT_SEEDS),
        "created_routines": len(ROUTINE_SEEDS),
        "created_identities": 0,
        "canonical_agents": len(AGENT_SEEDS),
        "canonical_projects": len(PROJECT_SEEDS),
        "canonical_routines": len(ROUTINE_SEEDS),
        "canonical_identities": 0,
    }

    pmo = db_session.scalar(select(Agent).where(Agent.key == "PMO_IA"))
    assert pmo is not None
    assert pmo.status == AgentStatus.disabled
    pmo.status = AgentStatus.active

    agrolog = db_session.scalar(select(Project).where(Project.key == "AGROLOG_MT"))
    assert agrolog is not None
    agrolog.priority = 0

    routine = db_session.scalar(select(Routine).where(Routine.key == "CONTROL_PLANE_HEALTH"))
    assert routine is not None
    original_due = routine.next_due_at
    routine.enabled = False
    db_session.commit()

    second = bootstrap_canonical_portfolio(db_session)
    assert second["created_agents"] == 0
    assert second["created_projects"] == 0
    assert second["created_routines"] == 0
    assert second["created_identities"] == 0
    assert pmo.status == AgentStatus.active
    assert agrolog.priority == 0
    assert routine.enabled is False
    assert routine.next_due_at == original_due


def test_canonical_hierarchy_keeps_pecuaria_and_maritime_inside_agrolog(db_session):
    bootstrap_canonical_portfolio(db_session)
    projects = {item.key: item for item in db_session.scalars(select(Project))}

    agrolog = projects["AGROLOG_MT"]
    assert projects["PECUARIA"].parent_project_id == agrolog.id
    assert projects["MARITIME_INTELLIGENCE"].parent_project_id == agrolog.id
    assert projects["PECUARIA"].repository == "brunocapellari-dotcom/AgroLogMT"
    assert projects["MARITIME_INTELLIGENCE"].repository == "brunocapellari-dotcom/AgroLogMT"


def test_bootstrap_does_not_claim_unprovisioned_agents_are_active(db_session):
    bootstrap_canonical_portfolio(db_session)
    agents = list(db_session.scalars(select(Agent)))
    assert agents
    assert all(agent.status == AgentStatus.disabled for agent in agents)
    assert all(agent.model_policy == {"status": "unconfigured"} for agent in agents)


def test_bootstrap_seeds_bounded_health_routine_without_enabling_agent(db_session):
    bootstrap_canonical_portfolio(db_session)
    routine = db_session.scalar(select(Routine).where(Routine.key == "CONTROL_PLANE_HEALTH"))
    pmo = db_session.scalar(select(Agent).where(Agent.key == "PMO_IA"))
    holding = db_session.scalar(select(Project).where(Project.key == "AI_HOLDING"))

    assert routine is not None
    assert pmo is not None
    assert holding is not None
    assert routine.project_id == holding.id
    assert routine.assigned_agent_id == pmo.id
    assert routine.execution_kind == "control_plane_health"
    assert routine.interval_minutes == 10
    assert routine.priority == 5
    assert routine.enabled is True
    assert pmo.status == AgentStatus.disabled


def test_bootstrap_seeds_knowledge_maintenance_without_activating_agent(db_session):
    bootstrap_canonical_portfolio(db_session)
    knowledge_agent = db_session.scalar(select(Agent).where(Agent.key == "KNOWLEDGE_IA"))
    second_brain = db_session.scalar(select(Project).where(Project.key == "SECOND_BRAIN"))
    routines = {
        item.key: item
        for item in db_session.scalars(
            select(Routine).where(
                Routine.key.in_(("KNOWLEDGE_GAP_SCAN", "KNOWLEDGE_OUTCOME_REVIEW"))
            )
        )
    }

    assert knowledge_agent is not None
    assert second_brain is not None
    assert knowledge_agent.status == AgentStatus.disabled
    assert routines["KNOWLEDGE_GAP_SCAN"].project_id == second_brain.id
    assert routines["KNOWLEDGE_GAP_SCAN"].assigned_agent_id == knowledge_agent.id
    assert routines["KNOWLEDGE_GAP_SCAN"].execution_kind == "knowledge_gap_scan"
    assert routines["KNOWLEDGE_GAP_SCAN"].interval_minutes == 360
    assert routines["KNOWLEDGE_OUTCOME_REVIEW"].project_id == second_brain.id
    assert routines["KNOWLEDGE_OUTCOME_REVIEW"].assigned_agent_id == knowledge_agent.id
    assert routines["KNOWLEDGE_OUTCOME_REVIEW"].execution_kind == "knowledge_outcome_review"
    assert routines["KNOWLEDGE_OUTCOME_REVIEW"].interval_minutes == 1440
    assert all(item.enabled for item in routines.values())


def test_runtime_identity_binding_is_idempotent_and_does_not_activate_agent(db_session):
    identity = RuntimeIdentitySeed(
        agent_key="PMO_IA",
        issuer="https://accounts.google.com",
        subject="868946857614000000001",
        email="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
    )

    first = bootstrap_canonical_portfolio(db_session, runtime_identities=(identity,))
    assert first["created_identities"] == 1
    assert first["canonical_identities"] == 1

    pmo = db_session.scalar(select(Agent).where(Agent.key == "PMO_IA"))
    assert pmo is not None
    assert pmo.status == AgentStatus.disabled

    binding = db_session.scalar(select(AgentIdentity).where(AgentIdentity.agent_id == pmo.id))
    assert binding is not None
    assert binding.issuer == identity.issuer
    assert binding.subject == identity.subject
    assert binding.email == identity.email

    second = bootstrap_canonical_portfolio(db_session, runtime_identities=(identity,))
    assert second["created_identities"] == 0


def test_runtime_identity_drift_fails_closed(db_session):
    identity = RuntimeIdentitySeed(
        agent_key="PMO_IA",
        issuer="https://accounts.google.com",
        subject="subject-1",
        email="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
    )
    bootstrap_canonical_portfolio(db_session, runtime_identities=(identity,))

    drifted = RuntimeIdentitySeed(
        agent_key="PMO_IA",
        issuer="https://accounts.google.com",
        subject="subject-2",
        email=identity.email,
    )
    with pytest.raises(RuntimeError, match="runtime identity drift detected"):
        bootstrap_canonical_portfolio(db_session, runtime_identities=(drifted,))


def test_runtime_identity_environment_requires_complete_configuration(monkeypatch):
    monkeypatch.delenv("PMO_IDENTITY_ISSUER", raising=False)
    monkeypatch.delenv("PMO_IDENTITY_SUBJECT", raising=False)
    monkeypatch.delenv("PMO_IDENTITY_EMAIL", raising=False)
    assert _runtime_identity_seeds_from_env() == ()

    monkeypatch.setenv("PMO_IDENTITY_SUBJECT", "subject-only")
    with pytest.raises(RuntimeError, match="configuration must be complete"):
        _runtime_identity_seeds_from_env()


def test_bootstrap_hydrates_missing_canonical_repository(db_session):
    bootstrap_canonical_portfolio(db_session)
    project = db_session.scalar(select(Project).where(Project.key == "MERCADO_FINANCEIRO"))
    assert project is not None
    assert project.repository == "brunocapellari-dotcom/Mercado-Financeiro"

    project.repository = None
    db_session.commit()

    second = bootstrap_canonical_portfolio(db_session)
    assert second["created_projects"] == 0
    assert project.repository == "brunocapellari-dotcom/Mercado-Financeiro"


def test_maintenance_field_intelligence_starts_as_incubating(db_session):
    bootstrap_canonical_portfolio(db_session)
    project = db_session.scalar(
        select(Project).where(Project.key == "MAINTENANCE_FIELD_INTELLIGENCE")
    )
    assert project is not None
    assert project.status == ProjectStatus.incubating


def test_owner_identity_bootstrap_is_optional_and_idempotent(db_session, monkeypatch):
    for name in ("OWNER_IDENTITY_ISSUER", "OWNER_IDENTITY_SUBJECT", "OWNER_IDENTITY_EMAIL"):
        monkeypatch.delenv(name, raising=False)
    assert bootstrap_owner_identity(db_session) is False

    monkeypatch.setenv("OWNER_IDENTITY_ISSUER", "https://accounts.google.com")
    monkeypatch.setenv("OWNER_IDENTITY_SUBJECT", "owner-subject")
    monkeypatch.setenv("OWNER_IDENTITY_EMAIL", "owner@example.com")

    assert bootstrap_owner_identity(db_session) is True
    db_session.commit()
    assert bootstrap_owner_identity(db_session) is False

    binding = db_session.query(HumanIdentityRole).one()
    assert binding.subject == "owner-subject"
    assert binding.email == "owner@example.com"
    assert binding.role == HumanRole.owner.value


def test_owner_identity_bootstrap_fails_closed_on_partial_configuration(
    db_session,
    monkeypatch,
):
    monkeypatch.setenv("OWNER_IDENTITY_ISSUER", "https://accounts.google.com")
    monkeypatch.setenv("OWNER_IDENTITY_SUBJECT", "owner-subject")
    monkeypatch.delenv("OWNER_IDENTITY_EMAIL", raising=False)

    with pytest.raises(RuntimeError, match="must be complete"):
        bootstrap_owner_identity(db_session)


def test_owner_identity_bootstrap_rejects_identity_drift(db_session, monkeypatch):
    monkeypatch.setenv("OWNER_IDENTITY_ISSUER", "https://accounts.google.com")
    monkeypatch.setenv("OWNER_IDENTITY_SUBJECT", "owner-subject")
    monkeypatch.setenv("OWNER_IDENTITY_EMAIL", "owner@example.com")
    assert bootstrap_owner_identity(db_session) is True
    db_session.commit()

    monkeypatch.setenv("OWNER_IDENTITY_EMAIL", "different@example.com")
    with pytest.raises(RuntimeError, match="owner identity drift"):
        bootstrap_owner_identity(db_session)


def test_bootstrap_contains_shared_execution_projects(db_session):
    bootstrap_canonical_portfolio(db_session)
    projects = {item.key: item for item in db_session.scalars(select(Project))}

    expected = {
        "RESEARCH_AI": "brunocapellari-dotcom/Research-AI",
        "CONTENT_FACTORY": "brunocapellari-dotcom/Content-Factory",
        "WHATSAPP_AI": "brunocapellari-dotcom/WHATSAPP_AI",
    }
    for key, repository in expected.items():
        assert key in projects
        assert projects[key].repository == repository
        assert projects[key].status in {ProjectStatus.active, ProjectStatus.incubating}
