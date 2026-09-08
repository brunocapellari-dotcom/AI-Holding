from app.core.actor import ActorContext, get_actor
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus, Project, Task, WorkStatus


def _service_actor() -> ActorContext:
    return ActorContext(
        name="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        actor_type="service-account",
        subject="subject-pmo-route",
        issuer="https://accounts.google.com",
        authenticated=True,
    )


def _human_actor() -> ActorContext:
    return ActorContext(
        name="operator@example.com",
        actor_type="human",
        subject="human-subject",
        issuer="https://accounts.google.com",
        authenticated=True,
    )


def _seed_runtime(db_session):
    pmo = Agent(
        key="PMO_IA",
        name="PMO IA",
        role="Portfolio execution and dependency manager",
        status=AgentStatus.active,
        max_autonomy=4,
        model_policy={"status": "unconfigured"},
        capabilities=["task-routing"],
    )
    other = Agent(
        key="OTHER_AGENT",
        name="Other Agent",
        role="Unrelated worker",
        status=AgentStatus.active,
        max_autonomy=4,
        model_policy={"status": "unconfigured"},
        capabilities=[],
    )
    db_session.add_all([pmo, other])
    db_session.flush()
    db_session.add(
        AgentIdentity(
            agent_id=pmo.id,
            issuer="https://accounts.google.com",
            subject="subject-pmo-route",
            email="holding-pmo-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        )
    )
    project = Project(
        key="AUTHZ_ROUTE",
        name="Authorization Route Test",
        priority=1,
        autonomy_level=4,
        strategic_goal="Verify production authorization boundaries.",
    )
    db_session.add(project)
    db_session.flush()
    task = Task(
        key="AUTHZ_READY",
        project_id=project.id,
        title="Authorized claim test",
        status=WorkStatus.ready,
        priority=0,
        idempotency_key="authz-route-ready-0001",
    )
    db_session.add(task)
    db_session.commit()
    return pmo, other, project, task


def test_bound_pmo_can_only_use_explicit_route_permissions(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    pmo, other, project, _ = _seed_runtime(db_session)
    client.app.dependency_overrides[get_actor] = _service_actor
    try:
        allowed_policy = client.post(
            "/api/v1/policy/evaluate",
            json={
                "action_key": "PMO_INTERNAL_READ",
                "project_id": str(project.id),
                "agent_id": str(pmo.id),
                "action_type": "internal_read",
                "summary": "Read canonical project state",
            },
        )
        assert allowed_policy.status_code == 200, allowed_policy.text

        impersonation = client.post(
            "/api/v1/policy/evaluate",
            json={
                "action_key": "OTHER_INTERNAL_READ",
                "project_id": str(project.id),
                "agent_id": str(other.id),
                "action_type": "internal_read",
                "summary": "Attempt to evaluate for another agent",
            },
        )
        assert impersonation.status_code == 403

        incident = client.post(
            "/api/v1/incidents",
            json={
                "project_id": str(project.id),
                "severity": "sev3",
                "title": "Worker detected deterministic failure",
                "source": "pmo-worker",
            },
        )
        assert incident.status_code == 201, incident.text

        transition = client.post(
            f"/api/v1/incidents/{incident.json()['id']}/transition",
            json={"status": "investigating"},
        )
        assert transition.status_code == 403

        privileged_project_write = client.post(
            "/api/v1/projects",
            json={
                "key": "FORBIDDEN_PROJECT",
                "name": "Forbidden Project",
                "priority": 1,
                "autonomy_level": 1,
                "strategic_goal": "This write must not be allowed to a service agent.",
            },
        )
        assert privileged_project_write.status_code == 403

        privileged_agent_write = client.post(
            "/api/v1/agents",
            json={"key": "FORBIDDEN_AGENT", "name": "Forbidden Agent", "role": "No access"},
        )
        assert privileged_agent_write.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_human_operator_cannot_use_service_only_claim_endpoint(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    pmo, _, _, _ = _seed_runtime(db_session)
    client.app.dependency_overrides[get_actor] = _human_actor
    try:
        response = client.post(
            "/api/v1/pmo/claim",
            json={"agent_id": str(pmo.id)},
        )
        assert response.status_code == 403
        assert "canonical service agent" in response.json()["detail"]
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_unbound_service_account_is_denied_at_route_boundary(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    _, _, project, _ = _seed_runtime(db_session)

    def unbound_actor() -> ActorContext:
        return ActorContext(
            name="unknown@ai-holding-prod-bc.iam.gserviceaccount.com",
            actor_type="service-account",
            subject="unbound-subject",
            issuer="https://accounts.google.com",
            authenticated=True,
        )

    client.app.dependency_overrides[get_actor] = unbound_actor
    try:
        incident = client.post(
            "/api/v1/incidents",
            json={
                "project_id": str(project.id),
                "severity": "sev3",
                "title": "Unauthorized incident",
                "source": "unknown-worker",
            },
        )
        assert incident.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_actor, None)
