from app.core.actor import ActorContext, get_actor
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus, AuditEvent


def _bind_agent(db_session, *, key: str, subject: str, email: str) -> None:
    agent = Agent(
        key=key,
        name=key,
        role="test",
        status=AgentStatus.active,
        max_autonomy=3,
        model_policy={"status": "unconfigured"},
        capabilities=[],
    )
    db_session.add(agent)
    db_session.flush()
    db_session.add(
        AgentIdentity(
            agent_id=agent.id,
            issuer="https://accounts.google.com",
            subject=subject,
            email=email,
        )
    )
    db_session.commit()


def _actor(*, subject: str, email: str) -> ActorContext:
    return ActorContext(
        name=email,
        actor_type="service-account",
        subject=subject,
        issuer="https://accounts.google.com",
        authenticated=True,
    )


def test_auditor_can_query_audit_events_with_filters_and_bounds(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "environment", "production")
    _bind_agent(
        db_session,
        key="AUDITOR_IA",
        subject="auditor-subject",
        email="auditor@example.iam.gserviceaccount.com",
    )
    db_session.add_all(
        [
            AuditEvent(
                actor="owner@example.com",
                actor_type="human",
                action="project.updated",
                entity_type="project",
                entity_id="project-1",
                payload={"safe": True},
            ),
            AuditEvent(
                actor="pmo",
                actor_type="service-account",
                action="task.claimed",
                entity_type="task",
                entity_id="task-1",
                payload={},
            ),
        ]
    )
    db_session.commit()

    client.app.dependency_overrides[get_actor] = lambda: _actor(
        subject="auditor-subject",
        email="auditor@example.iam.gserviceaccount.com",
    )
    try:
        response = client.get(
            "/api/v1/audit/events",
            params={"action": "project.updated", "limit": 500, "offset": -10},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body) == 1
        assert body[0]["entity_id"] == "project-1"
        assert body[0]["payload"] == {"safe": True}
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_pmo_cannot_read_audit_events(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    _bind_agent(
        db_session,
        key="PMO_IA",
        subject="pmo-audit-subject",
        email="pmo@example.iam.gserviceaccount.com",
    )
    client.app.dependency_overrides[get_actor] = lambda: _actor(
        subject="pmo-audit-subject",
        email="pmo@example.iam.gserviceaccount.com",
    )
    try:
        response = client.get("/api/v1/audit/events")
        assert response.status_code == 403
        assert "audit" in response.json()["detail"]
    finally:
        client.app.dependency_overrides.pop(get_actor, None)
