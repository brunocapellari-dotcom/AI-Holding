from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class HealthDimension(StrEnum):
    SOURCE = "SOURCE"
    COLLECTOR = "COLLECTOR"
    PIPELINE = "PIPELINE"
    STORAGE = "STORAGE"
    CI = "CI"


class HealthStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    BLOCKED_EXTERNAL = "BLOCKED_EXTERNAL"


@dataclass(frozen=True)
class HealthSignal:
    dimension: HealthDimension
    status: HealthStatus
    component: str
    detail: str | None = None


def collector_operational(signals: tuple[HealthSignal, ...], component: str) -> bool:
    relevant = [
        item
        for item in signals
        if item.component == component
        and item.dimension in {HealthDimension.SOURCE, HealthDimension.COLLECTOR}
    ]
    return bool(relevant) and all(item.status == HealthStatus.HEALTHY for item in relevant)
