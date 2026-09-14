from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.entities import Run, Task
from app.models.knowledge import KnowledgeEpistemicStatus
from app.schemas.knowledge import KnowledgeClaimIngest, KnowledgeEvidence
from app.services.knowledge import ingest_claim


def capture_run_learning(
    db: Session,
    *,
    run: Run,
    task: Task,
    actor_agent_id: UUID | None,
) -> list[UUID]:
    if run.status.value != "succeeded":
        return []

    output = dict(run.output_metadata or {})
    learning_items = output.get("knowledge")
    if not isinstance(learning_items, list):
        return []

    created_claim_ids: list[UUID] = []
    for item in learning_items:
        if not isinstance(item, dict):
            continue
        statement = item.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            continue

        source_name = item.get("source_name")
        source_uri = item.get("source_uri")
        confidence_raw = item.get("confidence", 0.5)
        try:
            confidence = min(max(float(confidence_raw), 0.0), 1.0)
        except (TypeError, ValueError):
            confidence = 0.5

        evidence: list[KnowledgeEvidence] = []
        evidence_raw = item.get("evidence", [])
        if isinstance(evidence_raw, list):
            for entry in evidence_raw:
                if isinstance(entry, dict) and isinstance(entry.get("source"), str):
                    evidence.append(KnowledgeEvidence.model_validate(entry))

        payload = KnowledgeClaimIngest(
            namespace=str(item.get("namespace") or "shared"),
            project_id=task.project_id,
            created_by_agent_id=actor_agent_id,
            statement=statement.strip(),
            epistemic_status=KnowledgeEpistemicStatus.inferred,
            confidence=confidence,
            source_name=str(source_name or "agent-run"),
            source_uri=str(source_uri) if source_uri else None,
            source_published_at=datetime.now(UTC),
            evidence=evidence,
            tags=["agent-feedback", f"task:{task.key}"],
            metadata_json={
                "origin": "run_feedback",
                "run_id": str(run.id),
                "task_id": str(task.id),
                "execution_kind": task.execution_kind,
            },
        )
        claim, created, _ = ingest_claim(
            db,
            payload,
            created_by_agent_id=actor_agent_id,
        )
        if created:
            created_claim_ids.append(claim.id)

    return created_claim_ids
