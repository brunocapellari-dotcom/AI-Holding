from uuid import uuid4


def create_project(client, key: str, autonomy: int = 4):
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": f"Project {key}",
            "priority": 1,
            "autonomy_level": autonomy,
            "strategic_goal": "Operate safely under deterministic autonomy policy.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_agent(client, key: str, autonomy: int = 4):
    response = client.post(
        "/api/v1/agents",
        json={
            "key": key,
            "name": f"Agent {key}",
            "role": "Policy test agent",
            "max_autonomy": autonomy,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def policy_payload(project, agent, action_key: str, action_type: str, **overrides):
    payload = {
        "action_key": action_key,
        "project_id": project["id"],
        "agent_id": agent["id"],
        "action_type": action_type,
        "summary": f"Execute {action_type} for the project",
    }
    payload.update(overrides)
    return payload


def test_policy_allows_reversible_internal_work_within_autonomy(client):
    project = create_project(client, "POLICY_ALLOW", 4)
    agent = create_agent(client, "AGENT_ALLOW", 4)

    response = client.post(
        "/api/v1/policy/evaluate",
        json=policy_payload(project, agent, "ALLOW_WRITE", "internal_write"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["outcome"] == "allow"
    assert body["required_autonomy"] == 3
    assert body["effective_autonomy"] == 4
    assert body["decision_id"] is None


def test_policy_denies_action_above_effective_autonomy(client):
    project = create_project(client, "POLICY_DENY_LEVEL", 4)
    agent = create_agent(client, "AGENT_LOW", 2)

    response = client.post(
        "/api/v1/policy/evaluate",
        json=policy_payload(project, agent, "DENY_PROD", "deploy_production"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "deny"
    assert body["effective_autonomy"] == 2
    assert "requires A4" in " ".join(body["reasons"])


def test_human_gate_is_idempotent_and_approved_decision_unlocks_exact_action(client):
    project = create_project(client, "POLICY_HUMAN", 5)
    agent = create_agent(client, "AGENT_HUMAN", 5)
    payload = policy_payload(project, agent, "PURCHASE_001", "purchase", financial_value="10.00")

    first = client.post("/api/v1/policy/evaluate", json=payload)
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["outcome"] == "require_human"
    assert first_body["decision_id"] is not None

    replay = client.post("/api/v1/policy/evaluate", json=payload)
    assert replay.status_code == 200
    assert replay.json()["decision_id"] == first_body["decision_id"]

    approved = client.post(
        f"/api/v1/decisions/{first_body['decision_id']}/resolve",
        json={"outcome": "approved", "rationale": "Approved for this exact action."},
    )
    assert approved.status_code == 200, approved.text

    after_approval = client.post("/api/v1/policy/evaluate", json=payload)
    assert after_approval.status_code == 200
    assert after_approval.json()["outcome"] == "allow"
    assert after_approval.json()["decision_id"] == first_body["decision_id"]


def test_policy_action_key_cannot_be_reused_with_different_context(client):
    project = create_project(client, "POLICY_COLLISION", 5)
    agent = create_agent(client, "AGENT_COLLISION", 5)
    original = policy_payload(project, agent, "LEGAL_001", "legal_commitment")

    assert client.post("/api/v1/policy/evaluate", json=original).status_code == 200
    changed = dict(original)
    changed["summary"] = "Different legal commitment using the same action key"
    collision = client.post("/api/v1/policy/evaluate", json=changed)
    assert collision.status_code == 409


def test_policy_fails_closed_for_sensitive_external_data(client):
    project = create_project(client, "POLICY_DATA", 6)
    agent = create_agent(client, "AGENT_DATA", 6)

    response = client.post(
        "/api/v1/policy/evaluate",
        json=policy_payload(
            project,
            agent,
            "DATA_EXPORT",
            "external_communication",
            sensitive_data=True,
            external_party_effect=True,
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "deny"
    assert body["decision_id"] is None
    assert "sensitive data" in " ".join(body["reasons"])


def test_degraded_agent_is_capped_and_disabled_agent_is_denied(client):
    project = create_project(client, "POLICY_AGENT_STATE", 6)
    agent = create_agent(client, "AGENT_STATE", 6)

    degraded = client.post(
        f"/api/v1/agents/{agent['id']}/transition",
        json={"status": "degraded"},
    )
    assert degraded.status_code == 200
    evaluation = client.post(
        "/api/v1/policy/evaluate",
        json=policy_payload(project, agent, "DEGRADED_RESEARCH", "internal_research"),
    )
    assert evaluation.status_code == 200
    assert evaluation.json()["outcome"] == "deny"
    assert evaluation.json()["effective_autonomy"] == 1

    disabled = client.post(
        f"/api/v1/agents/{agent['id']}/transition",
        json={"status": "disabled"},
    )
    assert disabled.status_code == 200
    read_eval = client.post(
        "/api/v1/policy/evaluate",
        json=policy_payload(project, agent, "DISABLED_READ", "internal_read"),
    )
    assert read_eval.status_code == 200
    assert read_eval.json()["outcome"] == "deny"


def test_policy_requires_human_for_high_risk_and_irreversible_actions(client):
    project = create_project(client, "POLICY_RISK", 6)
    agent = create_agent(client, "AGENT_RISK", 6)

    high_risk = client.post(
        "/api/v1/policy/evaluate",
        json=policy_payload(
            project,
            agent,
            "HIGH_RISK_WRITE",
            "internal_write",
            risk_level="high",
        ),
    )
    assert high_risk.status_code == 200
    assert high_risk.json()["outcome"] == "require_human"

    irreversible = client.post(
        "/api/v1/policy/evaluate",
        json=policy_payload(
            project,
            agent,
            "IRREVERSIBLE_WRITE",
            "internal_write",
            irreversible=True,
        ),
    )
    assert irreversible.status_code == 200
    assert irreversible.json()["outcome"] == "require_human"


def test_policy_rejects_missing_project_or_agent(client):
    project = create_project(client, "POLICY_MISSING", 4)
    agent = create_agent(client, "AGENT_PRESENT", 4)

    missing_project = policy_payload(project, agent, "MISSING_PROJECT", "internal_read")
    missing_project["project_id"] = str(uuid4())
    assert client.post("/api/v1/policy/evaluate", json=missing_project).status_code == 404

    missing_agent = policy_payload(project, agent, "MISSING_AGENT", "internal_read")
    missing_agent["agent_id"] = str(uuid4())
    assert client.post("/api/v1/policy/evaluate", json=missing_agent).status_code == 404
