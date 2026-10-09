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
            "strategic_goal": (
                "Operar inteligência agro e logística com confiabilidade institucional."
            ),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_project_hierarchy_supports_agrolog_modules(client):
    parent = create_project(client)
    child = client.post(
        "/api/v1/projects",
        json={
            "key": "PECUARIA",
            "name": "Inteligência Pecuária",
            "priority": 0,
            "autonomy_level": 4,
            "parent_project_id": parent["id"],
            "repository": "brunocapellari-dotcom/AgroLogMT",
            "repository_path": "domains/pecuaria",
            "business_unit": "Agronegócio e Logística",
            "strategic_goal": "Operar inteligência pecuária com governança própria.",
        },
    )
    assert child.status_code == 201, child.text
    assert child.json()["parent_project_id"] == parent["id"]
    assert child.json()["repository_path"] == "domains/pecuaria"

    invalid = client.post(
        "/api/v1/projects",
        json={
            "key": "INVALID_CHILD",
            "name": "Invalid Child",
            "priority": 3,
            "autonomy_level": 2,
            "parent_project_id": "00000000-0000-0000-0000-000000000001",
            "strategic_goal": "This must not be accepted without a valid parent.",
        },
    )
    assert invalid.status_code == 400


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
        (
            f"/api/v1/projects/{project['id']}/milestones/{milestone['id']}"
            f"/criteria/{criterion['id']}/verify"
        ),
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
        "evidence_required": False,
        "idempotency_key": "agrolog-task-001",
    }
    first = client.post("/api/v1/tasks", json=payload)
    second = client.post("/api/v1/tasks", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    task_id = first.json()["id"]
    ready = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        json={"status": "ready"},
    )
    running = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        json={"status": "running"},
    )
    invalid_done = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        json={"status": "done"},
    )
    review = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        json={"status": "review"},
    )
    done = client.post(
        f"/api/v1/tasks/{task_id}/transition",
        json={"status": "done"},
    )

    assert ready.status_code == 200
    assert running.status_code == 200
    assert invalid_done.status_code == 409
    assert review.status_code == 200
    assert done.status_code == 200


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
