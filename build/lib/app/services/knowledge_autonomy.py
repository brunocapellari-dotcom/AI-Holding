from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.entities import Run, RunStatus, Task
from app.models.knowledge import EpistemicStatus
from app.schemas.knowledge import EvidenceRef, KnowledgeClaimIngest
from app.services.knowledge import ingest_claim


def _normalize_confidence(value: object) -> int:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 50
    if 0.0 <= parsed <= 1.0:
        parsed *= 100.0
    return min(max(int(round(parsed)), 0), 100)


def _parse_evidence(value: object) -> list[EvidenceRef]:
    if not isinstance(value, list):
        return []
    parsed: list[EvidenceRef] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        try:
            parsed.append(EvidenceRef.model_validate(item))
        except ValidationError:
            continue
    return parsed


def capture_run_learning(
    db: Session,
    *,
    run: Run,
    task: Task,
    actor_agent_id: UUID | None,
) -> list[UUID]:
    if run.status != RunStatus.succeeded:
        return []

    output = dict(run.output_metadata or {})
    learning_items = output.get("knowledge")
    if not isinstance(learning_items, list):
        return []

    created_claim_ids: list[UUID] = []
    captured_at = datetime.now(UTC)
    for item in learning_items:
        if not isinstance(item, dict):
            continue
        statement = item.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            continue

        namespace = item.get("namespace")
        if not isinstance(namespace, str) or not namespace.strip():
            namespace = "shared"

        source_name = item.get("source_name")
        source_uri = item.get("source_uri")
        epistemic_raw = item.get("epistemic_status", EpistemicStatus.inferred.value)
        try:
            epistemic_status = EpistemicStatus(str(epistemic_raw))
        except ValueError:
            epistemic_status = EpistemicStatus.inferred

        try:
            payload = KnowledgeClaimIngest(
                namespace=namespace.strip().lower(),
                project_id=task.project_id,
                created_by_agent_id=actor_agent_id,
                statement=statement.strip(),
                epistemic_status=epistemic_status,
                confidence=_normalize_confidence(item.get("confidence", 50)),
                source_name=(
                    source_name.strip()
                    if isinstance(source_name, str) and source_name.strip()
                    else "agent-run"
                ),
                source_uri=(
                    source_uri.strip()
                    if isinstance(source_uri, str) and source_uri.strip()
                    else None
                ),
                evidence=_parse_evidence(item.get("evidence", [])),
                tags=["agent-feedback", f"task:{task.key}"],
                metadata_json={
                    "origin": "run_feedback",
                    "run_id": str(run.id),
                    "task_id": str(task.id),
                    "execution_kind": task.execution_kind,
                    "captured_at": captured_at.isoformat(),
                },
            )
        except ValidationError:
            continue

        claim, created, _ = ingest_claim(
            db,
            payload,
            created_by_agent_id=actor_agent_id,
        )
        if created:
            created_claim_ids.append(claim.id)

    return created_claim_ids
