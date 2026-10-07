from app.models.entities import Project, ProjectStatus, WorkStatus


def _project(client, key: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects",
        json={
            "key": key,
            "name": key,
            "priority": 0,
            "autonomy_level": 4,
            "strategic_goal": "Verify evidence-based control-plane governance",
            "metadata_json": {},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _task(client, project_id: str, key: str, **overrides) -> dict[str, object]:
    payload = {
        "key": key,
        "project_id": project_id,
        "title": f"{key} task",
        "description": "Operational acceptance task",
        "priority": 0,
        "auto_start": False,
        "depends_on": [],
        "acceptance_criteria": ["objective evidence exists"],
        "test_required": False,
        "evidence_required": True,
        "idempotency_key": f"idem-{key.lower()}-0001",
        "metadata_json": {},
    }
    payload.update(overrides)
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _transition(client, task_id: str, status: str, blocked_reason: str | None = None):
    payload = {"status": status, "blocked_reason": blocked_reason}
    return client.post(f"/api/v1/tasks/{task_id}/transition", json=payload)


def test_fake_done_is_rejected_until_verified_evidence_exists(client):
    project = _project(client, "FAKE_DONE")
    task = _task(client, str(project["id"]), "EVIDENCE_GATE")

    assert _transition(client, task["id"], "ready").status_code == 200
    assert _transition(client, task["id"], "running").status_code == 200
    assert _transition(client, task["id"], "review").status_code == 200

    rejected = _transition(client, task["id"], "done")
    assert rejected.status_code == 409
    assert "verified evidence" in str(rejected.json()["detail"])

    evidence = client.post(
        "/api/v1/holding/control-plane/evidence",
        json={
            "project_id": project["id"],
            "task_id": task["id"],
            "kind": "CI_RUN",
            "source": "github-actions",
            "artifact_reference": "run:fake-done-green",
            "metadata_json": {},
        },
    )
    assert evidence.status_code == 201, evidence.text
    verified = client.post(
        f"/api/v1/holding/control-plane/evidence/{evidence.json()['id']}/verify",
        json={"verification_status": "VERIFIED"},
    )
    assert verified.status_code == 200, verified.text

    accepted = _transition(client, task["id"], "done")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "done"


def test_test_required_task_needs_testing_and_passing_test(client):
    project = _project(client, "TEST_GATE")
    task = _task(
        client,
        str(project["id"]),
        "TEST_REQUIRED",
        evidence_required=False,
        test_required=True,
        commit_sha="abcdef1234567",
    )

    for state in ("ready", "running", "review"):
        assert _transition(client, task["id"], state).status_code == 200

    assert _transition(client, task["id"], "done").status_code == 409
    testing = _transition(client, task["id"], "testing")
    assert testing.status_code == 200, testing.text
    assert _transition(client, task["id"], "done").status_code == 409

    test = client.post(
        "/api/v1/holding/control-plane/tests",
        json={
            "project_id": project["id"],
            "task_id": task["id"],
            "suite": "task-e2e",
            "test_type": "E2E",
            "commit_sha": "abcdef1234567",
            "environment": "test",
            "result": "PASS",
            "failures": [],
            "metadata_json": {},
        },
    )
    assert test.status_code == 201, test.text
    done = _transition(client, task["id"], "done")
    assert done.status_code == 200, done.text


def test_paused_project_cannot_execute(client, db_session):
    project = _project(client, "PAUSED_GATE")
    task = _task(client, str(project["id"]), "PAUSED_TASK", evidence_required=False)
    model = db_session.get(Project, project["id"])
    assert model is not None
    model.status = ProjectStatus.paused
    db_session.commit()

    blocked = _transition(client, task["id"], "ready")
    assert blocked.status_code == 409
    assert "cannot receive executable work" in blocked.json()["detail"]


def test_wip_limit_blocks_fourth_running_task(client):
    project = _project(client, "WIP_GATE")
    tasks = [
        _task(client, str(project["id"]), f"WIP_{index}", evidence_required=False)
        for index in range(4)
    ]
    for task in tasks:
        assert _transition(client, task["id"], "ready").status_code == 200
    for task in tasks[:3]:
        running = _transition(client, task["id"], "running")
        assert running.status_code == 200, running.text

    fourth = _transition(client, tasks[3]["id"], "running")
    assert fourth.status_code == 409
    assert "WIP limit" in fourth.json()["detail"]


def test_release_cannot_be_ready_without_all_verified_gates(client):
    project = _project(client, "RELEASE_GATE")
    release = client.post(
        "/api/v1/holding/control-plane/releases",
        json={
            "project_id": project["id"],
            "name": "SELLABLE-1",
            "scope": ["control-plane-e2e"],
            "dependencies": [],
            "commercial_status": "NOT_READY",
            "metadata_json": {},
        },
    )
    assert release.status_code == 201, release.text
    release_id = release.json()["id"]

    rejected = client.post(
        f"/api/v1/holding/control-plane/releases/{release_id}/status",
        json={"status": "READY"},
    )
    assert rejected.status_code == 409
    assert "gate" in str(rejected.json()["detail"]).lower()

    evidence_by_kind = {
        "CODE": "COMMIT",
        "TEST": "TEST_RESULT",
        "SECURITY": "REPORT",
        "E2E": "E2E_EXECUTION",
        "DEPLOY": "DEPLOYMENT",
        "OPERATIONS": "ENDPOINT_HEALTH",
    }
    for gate_type, evidence_kind in evidence_by_kind.items():
        evidence = client.post(
            "/api/v1/holding/control-plane/evidence",
            json={
                "project_id": project["id"],
                "release_id": release_id,
                "kind": evidence_kind,
                "source": "acceptance-test",
                "artifact_reference": f"{gate_type.lower()}-evidence",
                "metadata_json": {},
            },
        )
        assert evidence.status_code == 201, evidence.text
        verified = client.post(
            f"/api/v1/holding/control-plane/evidence/{evidence.json()['id']}/verify",
            json={"verification_status": "VERIFIED"},
        )
        assert verified.status_code == 200, verified.text
        gate = client.put(
            f"/api/v1/holding/control-plane/releases/{release_id}/gates/{gate_type}",
            json={
                "gate_type": gate_type,
                "status": "PASS",
                "evidence_required": True,
                "notes": "verified by acceptance suite",
            },
        )
        assert gate.status_code == 200, gate.text

    ready = client.post(
        f"/api/v1/holding/control-plane/releases/{release_id}/status",
        json={"status": "READY"},
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["status"] == "READY"


def test_human_action_queue_and_owner_view_expose_real_blocker(client):
    project = _project(client, "HUMAN_GATE")
    blocker = client.post(
        "/api/v1/holding/control-plane/blockers",
        json={
            "project_id": project["id"],
            "blocker_type": "CREDENTIAL",
            "description": "Production credential missing",
            "impact": "Deploy cannot authenticate",
            "owner": "OWNER",
            "action_required": "Add production credential reference",
            "priority": "P0",
            "metadata_json": {},
        },
    )
    assert blocker.status_code == 201, blocker.text

    actions = client.get("/api/v1/holding/control-plane/human-actions")
    assert actions.status_code == 200
    assert any(item["kind"] == "BLOCKER" for item in actions.json())

    view = client.get("/api/v1/holding/control-plane/owner-view")
    assert view.status_code == 200, view.text
    row = next(item for item in view.json()["projects"] if item["key"] == "HUMAN_GATE")
    assert row["verified_status"] == "BLOCKED"
    assert row["open_blockers"] == 1
    assert row["next_best_action"] == "Add production credential reference"


def test_project_status_route_can_pause_but_not_accidentally_reactivate_discontinued(client):
    project = _project(client, "LIFECYCLE_GATE")
    paused = client.post(
        f"/api/v1/projects/{project['id']}/status",
        json={"status": "paused"},
    )
    assert paused.status_code == 200, paused.text
    assert paused.json()["status"] == "paused"

    discontinued = client.post(
        f"/api/v1/projects/{project['id']}/status",
        json={"status": "discontinued"},
    )
    assert discontinued.status_code == 200, discontinued.text
    assert discontinued.json()["status"] == "discontinued"

    rejected = client.post(
        f"/api/v1/projects/{project['id']}/status",
        json={"status": "active"},
    )
    assert rejected.status_code == 409
