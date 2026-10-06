from app.core.actor import ActorContext, get_actor
from app.core.config import settings
from app.models.agent_identity import AgentIdentity
from app.models.entities import Agent, AgentStatus, Project, Task, WorkStatus
from app.models.human_identity import HumanIdentityRole, HumanRole


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
        execution_kind="control_plane_health",
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
            json={
                "agent_id": str(pmo.id),
                "execution_kinds": ["control_plane_health"],
            },
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


def test_scoped_reads_prevent_cross_domain_service_access(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    pmo, _, _, _ = _seed_runtime(db_session)
    pmo.status = AgentStatus.active
    db_session.commit()

    client.app.dependency_overrides[get_actor] = _service_actor
    try:
        operational = client.get("/api/v1/holding/projects/registry")
        assert operational.status_code == 200, operational.text

        financial = client.get("/api/v1/holding/costs/summary")
        assert financial.status_code == 403
        assert "financial" in financial.json()["detail"]
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_knowledge_agent_is_bounded_to_knowledge_reads(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    knowledge = Agent(
        key="KNOWLEDGE_IA",
        name="Knowledge IA",
        role="Knowledge worker",
        status=AgentStatus.active,
        max_autonomy=4,
        model_policy={"status": "unconfigured"},
        capabilities=["knowledge-ingestion"],
    )
    db_session.add(knowledge)
    db_session.flush()
    db_session.add(
        AgentIdentity(
            agent_id=knowledge.id,
            issuer="https://accounts.google.com",
            subject="subject-knowledge-route",
            email="holding-knowledge-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
        )
    )
    db_session.commit()

    def knowledge_actor() -> ActorContext:
        return ActorContext(
            name="holding-knowledge-worker@ai-holding-prod-bc.iam.gserviceaccount.com",
            actor_type="service-account",
            subject="subject-knowledge-route",
            issuer="https://accounts.google.com",
            authenticated=True,
        )

    client.app.dependency_overrides[get_actor] = knowledge_actor
    try:
        knowledge_queue = client.get("/api/v1/knowledge/gaps")
        assert knowledge_queue.status_code == 200, knowledge_queue.text

        holding_state = client.get("/api/v1/holding/projects/registry")
        assert holding_state.status_code == 403
        assert "operational" in holding_state.json()["detail"]
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_bound_owner_can_read_sensitive_holding_domains(client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    db_session.add(
        HumanIdentityRole(
            issuer="https://accounts.google.com",
            subject="owner-route-subject",
            email="owner@example.com",
            role=HumanRole.owner.value,
        )
    )
    db_session.commit()

    def owner_actor() -> ActorContext:
        return ActorContext(
            name="owner@example.com",
            actor_type="human",
            subject="owner-route-subject",
            issuer="https://accounts.google.com",
            authenticated=True,
        )

    client.app.dependency_overrides[get_actor] = owner_actor
    try:
        for path in (
            "/api/v1/holding/projects/registry",
            "/api/v1/holding/costs/summary",
            "/api/v1/holding/security/findings",
            "/api/v1/holding/tool-decisions",
        ):
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_pmo_service_account_has_only_bounded_collector_mutations(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "environment", "production")
    pmo, _, project, _ = _seed_runtime(db_session)
    pmo.status = AgentStatus.active
    db_session.commit()

    client.app.dependency_overrides[get_actor] = _service_actor
    try:
        project_id = str(project.id)
        collector_payload = {
            "key": "github-repository",
            "source": "github-api",
            "data_type": "repository_and_ci_state",
            "frequency_seconds": 600,
            "freshness_sla_seconds": 1800,
            "retry_policy": {"max_attempts": 3},
            "status": "degraded",
            "last_success_at": None,
            "last_failure_at": None,
            "last_latency_ms": None,
            "consecutive_failures": 0,
            "metadata_json": {},
        }
        collector = client.put(
            f"/api/v1/holding/projects/{project_id}/collectors/github-repository",
            json=collector_payload,
        )
        assert collector.status_code == 200, collector.text

        execution = client.post(
            (f"/api/v1/holding/projects/{project_id}/collectors/github-repository/executions"),
            json={
                "status": "success",
                "started_at": "2026-09-18T12:00:00Z",
                "finished_at": "2026-09-18T12:00:01Z",
                "records_seen": 2,
                "records_written": 1,
                "evidence": [{"source": "test"}],
                "metadata_json": {},
            },
        )
        assert execution.status_code == 201, execution.text

        health = client.post(f"/api/v1/holding/projects/{project_id}/health/recompute")
        assert health.status_code == 200, health.text

        forbidden_risk = client.post(
            "/api/v1/holding/risks",
            json={
                "project_id": project_id,
                "key": "PMO_SCOPE_TEST",
                "description": "PMO must not create arbitrary risk records",
                "probability": 10,
                "impact": 1,
                "severity": "low",
                "mitigation": "",
                "owner": "risk-ai",
                "status": "open",
                "metadata_json": {},
            },
        )
        assert forbidden_risk.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_pmo_cannot_read_sensitive_project_contract_or_executive_state(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "environment", "production")
    pmo, project, _, _ = _seed_runtime(db_session)
    pmo.status = AgentStatus.active
    db_session.commit()

    client.app.dependency_overrides[get_actor] = _service_actor
    try:
        contract = client.get(f"/api/v1/holding/projects/{project.id}/contract")
        assert contract.status_code == 403
        assert "financial" in contract.json()["detail"]

        executive = client.get("/api/v1/holding/executive-state")
        assert executive.status_code == 403
        assert "financial" in executive.json()["detail"]
    finally:
        client.app.dependency_overrides.pop(get_actor, None)


def test_bound_owner_can_read_compound_executive_contract(
    client,
    db_session,
    monkeypatch,
):
    monkeypatch.setattr(settings, "environment", "production")
    _, project, _, _ = _seed_runtime(db_session)
    db_session.add(
        HumanIdentityRole(
            issuer="https://accounts.google.com",
            subject="owner-compound-subject",
            email="owner-compound@example.com",
            role=HumanRole.owner.value,
        )
    )
    db_session.commit()

    def owner_actor() -> ActorContext:
        return ActorContext(
            name="owner-compound@example.com",
            actor_type="human",
            subject="owner-compound-subject",
            issuer="https://accounts.google.com",
            authenticated=True,
        )

    client.app.dependency_overrides[get_actor] = owner_actor
    try:
        contract = client.get(f"/api/v1/holding/projects/{project.id}/contract")
        assert contract.status_code == 200, contract.text
        executive = client.get("/api/v1/holding/executive-state")
        assert executive.status_code == 200, executive.text
    finally:
        client.app.dependency_overrides.pop(get_actor, None)
