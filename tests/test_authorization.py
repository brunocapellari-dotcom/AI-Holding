from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.actor import ActorContext
from app.core.authorization import AgentPermission, ReadScope, authorize_mutation, authorize_read
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus
from app.models.human_identity import HumanIdentityRole, HumanRole


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


def human_actor(
    *,
    subject: str = "human-subject",
    email: str = "operator@example.com",
) -> ActorContext:
    return ActorContext(
        name=email,
        actor_type="human",
        subject=subject,
        issuer="https://accounts.google.com",
        authenticated=True,
    )


def bind_human(db_session, *, role: HumanRole, actor: ActorContext | None = None) -> None:
    actor = actor or human_actor()
    assert actor.issuer is not None
    assert actor.subject is not None
    db_session.add(
        HumanIdentityRole(
            issuer=actor.issuer,
            subject=actor.subject,
            email=actor.name,
            role=role.value,
        )
    )
    db_session.commit()


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


def test_production_unbound_human_is_denied_even_with_verified_identity(
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(db_session, human_actor())
    assert exc_info.value.status_code == 403
    assert "not bound" in exc_info.value.detail


def test_production_bound_owner_can_mutate(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    actor = human_actor(email="owner@example.com")
    bind_human(db_session, role=HumanRole.owner, actor=actor)
    assert authorize_mutation(db_session, actor) is None


@pytest.mark.parametrize("role", [HumanRole.operator, HumanRole.auditor, HumanRole.viewer])
def test_non_owner_human_roles_are_read_only(db_session, monkeypatch, role):
    monkeypatch.setattr(settings, "environment", "production")
    actor = human_actor()
    bind_human(db_session, role=role, actor=actor)

    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(db_session, actor)
    assert exc_info.value.status_code == 403
    assert "read-only" in exc_info.value.detail


def test_owner_binding_rejects_verified_email_drift(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    bound_actor = human_actor(email="owner@example.com")
    bind_human(db_session, role=HumanRole.owner, actor=bound_actor)

    drifted = human_actor(email="renamed@example.com")
    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(db_session, drifted)
    assert exc_info.value.status_code == 403
    assert "does not match" in exc_info.value.detail


def test_service_only_mutation_rejects_owner_human(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    actor = human_actor(email="owner@example.com")
    bind_human(db_session, role=HumanRole.owner, actor=actor)

    with pytest.raises(HTTPException) as exc_info:
        authorize_mutation(db_session, actor, allow_human=False)
    assert exc_info.value.status_code == 403
    assert "canonical service agent" in exc_info.value.detail


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


def test_human_read_scopes_are_fail_closed_and_role_bounded(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")

    owner = human_actor(email="owner@example.com")
    bind_human(db_session, role=HumanRole.owner, actor=owner)
    for scope in ReadScope:
        assert authorize_read(db_session, owner, scope=scope) == HumanRole.owner

    viewer = human_actor(subject="viewer-subject", email="viewer@example.com")
    bind_human(db_session, role=HumanRole.viewer, actor=viewer)
    assert authorize_read(db_session, viewer, scope=ReadScope.operational) == HumanRole.viewer
    with pytest.raises(HTTPException) as exc_info:
        authorize_read(db_session, viewer, scope=ReadScope.financial)
    assert exc_info.value.status_code == 403


def test_agent_read_scopes_block_cross_domain_access(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    pmo = create_bound_pmo(db_session)
    assert authorize_read(db_session, service_actor(), scope=ReadScope.operational) == pmo
    assert authorize_read(db_session, service_actor(), scope=ReadScope.governance) == pmo

    with pytest.raises(HTTPException) as exc_info:
        authorize_read(db_session, service_actor(), scope=ReadScope.financial)
    assert exc_info.value.status_code == 403

    knowledge = create_bound_knowledge(db_session)
    knowledge_actor = service_actor(subject="subject-knowledge")
    assert authorize_read(db_session, knowledge_actor, scope=ReadScope.knowledge) == knowledge

    with pytest.raises(HTTPException) as exc_info:
        authorize_read(db_session, knowledge_actor, scope=ReadScope.security)
    assert exc_info.value.status_code == 403


def test_unbound_human_cannot_read_scoped_data(db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(HTTPException) as exc_info:
        authorize_read(db_session, human_actor(), scope=ReadScope.operational)
    assert exc_info.value.status_code == 403
