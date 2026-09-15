from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.collector import Collector, CollectorStatus
from app.schemas.collectors import CollectorReport

FAILURE_THRESHOLD = 3
STALE_GRACE_SECONDS = 300


def collector_is_stale(collector: Collector, now: datetime | None = None) -> bool:
    if collector.status == CollectorStatus.disabled.value:
        return False
    if collector.frequency_seconds is None:
        return False
    if collector.last_collected_at is None:
        return True

    current = now or datetime.now(UTC)
    allowed_age = max(
        collector.frequency_seconds * 2,
        collector.frequency_seconds + STALE_GRACE_SECONDS,
    )
    return current - collector.last_collected_at > timedelta(seconds=allowed_age)


def record_collection(
    collector: Collector,
    report: CollectorReport,
    *,
    now: datetime | None = None,
) -> None:
    if collector.status == CollectorStatus.disabled.value:
        raise ValueError("disabled collector cannot report collection results")

    collected_at = now or datetime.now(UTC)
    collector.last_collected_at = collected_at
    collector.latency_ms = report.latency_ms
    collector.produced_data = report.produced_data

    if report.success:
        collector.status = CollectorStatus.healthy.value
        collector.last_success_at = collected_at
        collector.consecutive_failures = 0
        collector.last_error = None
        return

    collector.failure_count += 1
    collector.consecutive_failures += 1
    collector.last_error = report.error
    collector.status = (
        CollectorStatus.failed.value
        if collector.consecutive_failures >= FAILURE_THRESHOLD
        else CollectorStatus.degraded.value
    )


def set_collector_enabled(collector: Collector, enabled: bool) -> None:
    if not enabled:
        collector.status = CollectorStatus.disabled.value
        return

    if collector.last_success_at is not None and collector.consecutive_failures == 0:
        collector.status = CollectorStatus.healthy.value
    elif collector.consecutive_failures >= FAILURE_THRESHOLD:
        collector.status = CollectorStatus.failed.value
    else:
        collector.status = CollectorStatus.degraded.value
