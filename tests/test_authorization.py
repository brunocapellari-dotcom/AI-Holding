from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.actor import ActorContext
from app.core.authorization import AgentPermission, authorize_mutation
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus


def service_actor(subject: str = "subject-pmo") -> ActorContext:
    return ActorContext(
        name="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        actor_type="service-account",
        subject=subject,
        issuer="https://accounts.google.com",
        authenticated=True,
    )


def create_bound_pmo(db_session, *, status: AgentStatus = AgentStatus.active) -> Agent:
    agent = Agent(
        key="PMO_IA",
        name="PMO IA",
        role="Portfolio execution and dependency manager",
        status=status,
        max_autonomy=4,
        model_policy={"status": "unconfigured"},
        capabilities=["task-routing"],
    )
    db_session.add(agent)
    db_session.flush()
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject="subject-pmo",
            email="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        )
    )
    db_session.commit()
    return agent


def create_bound_knowledge(db_session) -> Agent:
    agent = Agent(
        key="KNOWLEDGE_IA",
        name="Knowledge IA",
        role="Universal knowledge ingestion and memory steward for all projects",
        status=AgentStatus.active,
        max_autonomy=4,
        model_policy={"status": "unconfigured"},
        capabilities=["knowledge-ingestion"],
    )
    db_session.add(agent)
    db_session.flush()
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject="subject-knowledge",
            email="holding-knowledge-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        )
    )
    db_session.commit()
    return agent


def test_local_environments_keep_test_mutations_available(db_session):
    actor = ActorContext(name="local-test", actor_type="service-account")
    assert authorize_mutation(db_session, actor) is None


def test_production_human_relies_on_cloud_run_iam_boundary(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    actor = ActorContext(
        name="operator@example.com",
        actor_type="human",
        subject="human-subject",
        issuer="https://accounts.google.com",
        authenticated=True,
    )
    assert authorize_mutation(db_session, actor) is None


def test_production_service_account_is_denied_without_binding(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(
            db_session,
            service_actor(),
            permission=AgentPermission.claim_work,
        )
    assert exc_info.value.status_code == 403
    assert "not bound" in exc_info.value.detail


def test_disabled_bound_agent_is_denied(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    create_bound_pmo(db_session, status=AgentStatus.disabled)

    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(
            db_session,
            service_actor(),
            permission=AgentPermission.claim_work,
        )
    assert exc_info.value.status_code == 403
    assert "not active" in exc_info.value.detail


def test_bound_pmo_gets_only_explicit_permissions(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    pmo = create_bound_pmo(db_session)

    authorized = authorize_mutation(
        db_session,
        service_actor(),
        permission=AgentPermission.claim_work,
        expected_agent_id=pmo.id,
    )
    assert authorized is not None
    assert authorized.id == pmo.id

    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(db_session, service_actor())
    assert exc_info.value.status_code == 403
    assert "not authorized" in exc_info.value.detail


def test_bound_knowledge_agent_has_worker_permissions_but_not_promotion(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    agent = create_bound_knowledge(db_session)
    actor = service_actor(subject="subject-knowledge")

    for permission in (
        AgentPermission.claim_work,
        AgentPermission.transition_own_task,
        AgentPermission.transition_own_run,
        AgentPermission.create_incident,
        AgentPermission.submit_knowledge,
        AgentPermission.submit_knowledge_outcome,
        AgentPermission.export_knowledge,
    ):
        authorized = authorize_mutation(
            db_session,
            actor,
            permission=permission,
            expected_agent_id=agent.id,
        )
        assert authorized is not None
        assert authorized.id == agent.id

    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(
            db_session,
            actor,
            permission=AgentPermission.promote_knowledge,
        )
    assert exc_info.value.status_code == 403
    assert "does not have this permission" in exc_info.value.detail


def test_service_account_cannot_act_as_another_agent(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    create_bound_pmo(db_session)

    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(
            db_session,
            service_actor(),
            permission=AgentPermission.transition_own_run,
            expected_agent_id=uuid4(),
        )
    assert exc_info.value.status_code == 403
    assert "another agent" in exc_info.value.detail
