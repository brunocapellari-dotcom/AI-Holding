def create_project(client):
    response = client.post(
        "/api/v1/projects",
        json={
            "key": "AGROLOG",
            "name": "AgroLog MT",
            "priority": 0,
            "autonomy_level": 4,
            "repository": "brunocapellari-dotcom/AgroLogMT",
            "business_unit": "Agronegócio e Logística",
            "strategic_goal": "Operar inteligência agro e logística com confiabilidade institucional.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_progress_is_evidence_based(client):
    project = create_project(client)
    milestone = client.post(
        f"/api/v1/projects/{project['id']}/milestones",
        json={
            "key": "METEO_PROD",
            "title": "Meteorologia em produção",
            "objective": "Publicar boletim meteorológico confiável e automatizado.",
            "weight": 10,
        },
    ).json()
    criterion = client.post(
        f"/api/v1/projects/{project['id']}/milestones/{milestone['id']}/criteria",
        json={
            "key": "FRESHNESS",
            "description": "Freshness das fontes validada antes da publicação.",
            "weight": 1,
        },
    ).json()

    before = client.get(f"/api/v1/projects/{project['id']}/progress").json()
    assert before["progress_pct"] == 0.0

    verified = client.post(
        f"/api/v1/projects/{project['id']}/milestones/{milestone['id']}/criteria/{criterion['id']}/verify",
        json={"evidence": ["ci://agrolog/freshness/2026-09-01"]},
    )
    assert verified.status_code == 200

    after = client.get(f"/api/v1/projects/{project['id']}/progress").json()
    assert after["progress_pct"] == 100.0
    assert after["criteria_verified"] == 1


def test_task_idempotency_and_state_machine(client):
    project = create_project(client)
    payload = {
        "key": "TASK_001",
        "project_id": project["id"],
        "title": "Validar pipeline",
        "priority": 1,
        "depends_on": [],
        "idempotency_key": "agrolog-task-001",
    }
    first = client.post("/api/v1/tasks", json=payload)
    second = client.post("/api/v1/tasks", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    task_id = first.json()["id"]
    assert client.post(f"/api/v1/tasks/{task_id}/transition", json={"status": "ready"}).status_code == 200
    assert client.post(f"/api/v1/tasks/{task_id}/transition", json={"status": "running"}).status_code == 200
    assert client.post(f"/api/v1/tasks/{task_id}/transition", json={"status": "done"}).status_code == 409
    assert client.post(f"/api/v1/tasks/{task_id}/transition", json={"status": "review"}).status_code == 200
    assert client.post(f"/api/v1/tasks/{task_id}/transition", json={"status": "done"}).status_code == 200


def test_decision_queue_requires_resolution(client):
    project = create_project(client)
    created = client.post(
        "/api/v1/decisions",
        json={
            "key": "BUY_SOURCE_X",
            "project_id": project["id"],
            "title": "Contratar fonte X",
            "context": "A fonte é paga e ultrapassa autonomia financeira do CEO IA.",
            "recommendation": "Contratar se SLA atender aos requisitos.",
            "risk_level": "high",
            "requires_human": True,
            "options": ["approve", "reject"],
        },
    )
    assert created.status_code == 201
    pending = client.get("/api/v1/decisions/pending-human").json()
    assert len(pending) == 1

    resolved = client.post(
        f"/api/v1/decisions/{created.json()['id']}/resolve",
        json={"outcome": "approved", "rationale": "Aprovado pelo proprietário."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "approved"
    assert client.get("/api/v1/decisions/pending-human").json() == []
