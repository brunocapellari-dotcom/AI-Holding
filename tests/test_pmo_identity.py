from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.actor import ActorContext
from app.core.authorization import AgentPermission, authorize_mutation
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus


def make_pmo(db_session) -> Agent:
    agent = Agent(
        key="PMO_IA",
        name="PMO IA",
        role="Portfolio execution and dependency manager",
        status=AgentStatus.active,
        max_autonomy=4,
        model_policy={"status": "unconfigured"},
        capabilities=["task-routing"],
    )
    db_session.add(agent)
    db_session.flush()
    return agent


def service_actor() -> ActorContext:
    return ActorContext(
        name="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        actor_type="service-account",
        subject="123456789",
        issuer="https://accounts.google.com",
        authenticated=True,
    )


def authorize_claim(db_session, agent: Agent, actor: ActorContext):
    return authorize_mutation(
        db_session,
        actor,
        permission=AgentPermission.claim_work,
        expected_agent_id=agent.id,
        allow_human=False,
    )


def bind_pmo(db_session, agent: Agent) -> None:
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject="123456789",
            email="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        )
    )
    db_session.flush()


def test_production_claim_rejects_unbound_service_identity(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_pmo(db_session)

    with pytest.raises(HTTPException) as exc_info:
        authorize_claim(db_session, agent, service_actor())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "service-account is not bound to a canonical agent"


def test_production_claim_accepts_matching_bound_identity(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_pmo(db_session)
    bind_pmo(db_session, agent)

    authorized = authorize_claim(db_session, agent, service_actor())

    assert authorized is not None
    assert authorized.id == agent.id


def test_production_claim_rejects_agent_impersonation(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_pmo(db_session)
    bind_pmo(db_session, agent)

    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(
            db_session,
            service_actor(),
            permission=AgentPermission.claim_work,
            expected_agent_id=uuid4(),
            allow_human=False,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "service-account cannot act as another agent"


def test_production_claim_rejects_human_actor(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = make_pmo(db_session)
    actor = ActorContext(
        name="admin@example.com",
        actor_type="human",
        subject="human-123",
        issuer="https://accounts.google.com",
        authenticated=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        authorize_claim(db_session, agent, actor)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "this mutation requires a canonical service agent"


def test_test_environment_bypasses_runtime_binding(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "test")
    agent = make_pmo(db_session)
    local_actor = ActorContext(name="test-agent", actor_type="agent")

    assert authorize_claim(db_session, agent, local_actor) is None
