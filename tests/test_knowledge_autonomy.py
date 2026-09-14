from app.models.entities import RunStatus
from app.models.knowledge import KnowledgeLifecycle
from app.services.knowledge_autonomy import capture_run_learning


def test_capture_run_learning_creates_raw_claim(db_session, seeded_project, seeded_agent, seeded_task):
    seeded_task.project_id = seeded_project.id
    seeded_task.assigned_agent_id = seeded_agent.id
    run = seeded_task.runs[0] if seeded_task.runs else None
    if run is None:
        from app.models.entities import Run

        run = Run(task_id=seeded_task.id, agent_id=seeded_agent.id)
        db_session.add(run)
        db_session.flush()

    run.status = RunStatus.succeeded
    run.output_metadata = {
        "knowledge": [
            {
                "namespace": "shared",
                "statement": "Completed executions can contribute reusable knowledge.",
                "confidence": 0.8,
                "source_name": "unit-test",
                "evidence": [{"source": "run", "locator": str(run.id)}],
            }
        ]
    }

    created = capture_run_learning(
        db_session,
        run=run,
        task=seeded_task,
        actor_agent_id=seeded_agent.id,
    )
    assert len(created) == 1
    claim = db_session.get(__import__("app.models.knowledge", fromlist=["KnowledgeClaim"]).KnowledgeClaim, created[0])
    assert claim is not None
    assert claim.lifecycle_status == KnowledgeLifecycle.raw.value
    assert claim.metadata_json["origin"] == "run_feedback"
