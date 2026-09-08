import pytest
from sqlalchemy import select

from app.bootstrap import (
    AGENT_SEEDS,
    PROJECT_SEEDS,
    RuntimeIdentitySeed,
    _runtime_identity_seeds_from_env,
    bootstrap_canonical_portfolio,
)
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus, Project, ProjectStatus


def test_canonical_bootstrap_is_idempotent_and_preserves_runtime_state(db_session):
    first = bootstrap_canonical_portfolio(db_session)
    assert first == {
        "created_agents": len(AGENT_SEEDS),
        "created_projects": len(PROJECT_SEEDS),
        "created_identities": 0,
        "canonical_agents": len(AGENT_SEEDS),
        "canonical_projects": len(PROJECT_SEEDS),
        "canonical_identities": 0,
    }

    pmo = db_session.scalar(select(Agent).where(Agent.key == "PMO_IA"))
    assert pmo is not None
    assert pmo.status == AgentStatus.disabled
    pmo.status = AgentStatus.active

    agrolog = db_session.scalar(select(Project).where(Project.key == "AGROLOG_MT"))
    assert agrolog is not None
    agrolog.priority = 0
    db_session.commit()

    second = bootstrap_canonical_portfolio(db_session)
    assert second["created_agents"] == 0
    assert second["created_projects"] == 0
    assert second["created_identities"] == 0
    assert pmo.status == AgentStatus.active
    assert agrolog.priority == 0


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

    binding = db_session.scalar(
        select(AgentIdentity).where(AgentIdentity.agent_id == pmo.id)
    )
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


def test_maintenance_field_intelligence_starts_as_incubating(db_session):
    bootstrap_canonical_portfolio(db_session)
    project = db_session.scalar(
        select(Project).where(Project.key == "MAINTENANCE_FIELD_INTELLIGENCE")
    )
    assert project is not None
    assert project.status == ProjectStatus.incubating
