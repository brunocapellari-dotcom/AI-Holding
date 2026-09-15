from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.holding import CollectorRegistration, HoldingAlert
from app.models.holding_evidence import CollectorExecution
from app.schemas.holding_evidence import CollectorExecutionCreate


def record_collector_execution_state(
    db: Session,
    *,
    project_id: UUID,
    collector: CollectorRegistration,
    execution: CollectorExecution,
    payload: CollectorExecutionCreate,
) -> None:
    """Update aggregate collector state while retaining execution history."""
    now = payload.finished_at or datetime.now(UTC)
    dedupe_key = f"collector-failing:{project_id}:{collector.key}"
    alert = db.scalar(select(HoldingAlert).where(HoldingAlert.dedupe_key == dedupe_key))

    if payload.status == "success":
        collector.status = "healthy"
        collector.last_success_at = payload.finished_at
        collector.consecutive_failures = 0
        if alert is not None:
            alert.status = "resolved"
            alert.last_seen_at = now
            alert.details = {
                "collector_key": collector.key,
                "recovered_execution_id": str(execution.id),
            }
    elif payload.status == "degraded":
        collector.status = "degraded"
        collector.last_success_at = payload.finished_at
    elif payload.status == "failure":
        collector.consecutive_failures += 1
        collector.last_failure_at = payload.finished_at
        collector.status = "failing" if collector.consecutive_failures >= 3 else "degraded"
        if collector.consecutive_failures >= 3:
            details = {
                "collector_key": collector.key,
                "consecutive_failures": collector.consecutive_failures,
                "execution_id": str(execution.id),
                "error_class": payload.error_class,
                "error_message": payload.error_message,
            }
            if alert is None:
                db.add(
                    HoldingAlert(
                        project_id=project_id,
                        level="action_required",
                        source="collector-health",
                        dedupe_key=dedupe_key,
                        title=f"Collector {collector.key} is failing",
                        details=details,
                        status="active",
                        occurrences=1,
                        last_seen_at=now,
                    )
                )
            else:
                alert.level = "action_required"
                alert.status = "active"
                alert.details = details
                alert.occurrences += 1
                alert.last_seen_at = now

    if payload.latency_ms is not None:
        collector.last_latency_ms = payload.latency_ms
