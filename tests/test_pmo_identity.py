import pytest
from fastapi import HTTPException

from app.api.routes.pmo import _require_claim_identity
from app.core.actor import ActorContext
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent


def make_agent(db_session) -> Agent:
    agent = Agent(
        key="IDENTITY_WORKER",
        name="Identity Worker",
        role="Bound execution worker",
    )
    db_session.add(agent)
    db_session.flush()
    return agent


def service_actor(*, subject: str = "123456789") -> ActorContext:
    return ActorContext(
        name="worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        actor_type="service-account",
        subject=subject,
        issuer="https://accounts.google.com",
        authenticated=True,
    )


def test_production_claim_rejects_unbound_agent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_agent(db_session)

    with pytest.raises(HTTPException) as exc_info:
        _require_claim_identity(db_session, agent=agent, actor=service_actor())

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "agent runtime identity is not bound"


def test_production_claim_accepts_matching_bound_identity(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_agent(db_session)
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject="123456789",
            email="worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        )
    )
    db_session.flush()

    _require_claim_identity(db_session, agent=agent, actor=service_actor())


def test_production_claim_rejects_identity_for_another_agent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_agent(db_session)
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject="123456789",
            email="worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        )
    )
    db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        _require_claim_identity(
            db_session,
            agent=agent,
            actor=service_actor(subject="987654321"),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "runtime identity does not match agent"


def test_production_claim_rejects_human_actor(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_agent(db_session)
    actor = ActorContext(
        name="admin@example.com",
        actor_type="human",
        subject="human-123",
        issuer="https://accounts.google.com",
        authenticated=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        _require_claim_identity(db_session, agent=agent, actor=actor)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "service-account identity is required"


def test_test_environment_bypasses_runtime_binding(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    agent = make_agent(db_session)
    local_actor = ActorContext(name="test-agent", actor_type="agent")

    _require_claim_identity(db_session, agent=agent, actor=local_actor)
