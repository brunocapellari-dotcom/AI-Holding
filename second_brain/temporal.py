from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from second_brain.schemas import LifecycleStatus, TemporalContext


class TemporalRecord(Protocol):
    status: LifecycleStatus
    temporal: TemporalContext


def _within(moment: datetime, start: datetime | None, end: datetime | None) -> bool:
    return (start is None or start <= moment) and (end is None or moment < end)


def visible_as_of(record: TemporalRecord, *, valid_at: datetime, known_at: datetime) -> bool:
    """Return whether a record was both true and known at the requested bitemporal point."""
    if record.status in {
        LifecycleStatus.PROPOSTO,
        LifecycleStatus.EM_REVISAO,
        LifecycleStatus.REJEITADO,
        LifecycleStatus.CONFLITANTE,
        LifecycleStatus.BAIXA_CONFIANCA,
    }:
        return False
    temporal = record.temporal
    return _within(valid_at, temporal.valid_from, temporal.valid_to) and _within(
        known_at, temporal.known_from, temporal.known_to
    )


def visible_now(record: TemporalRecord) -> bool:
    now = datetime.now(UTC)
    return visible_as_of(record, valid_at=now, known_at=now)
