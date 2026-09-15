from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from second_brain.schemas import InformationClass


class CollectorMethod(StrEnum):
    API = "API"
    RSS = "RSS"
    WEBSITE = "WEBSITE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"
    FOLDER = "FOLDER"
    UPLOAD = "UPLOAD"
    PROJECT_ADAPTER = "PROJECT_ADAPTER"


class CollectorHealth(StrEnum):
    UNKNOWN = "UNKNOWN"
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    DISABLED = "DISABLED"


@dataclass(frozen=True)
class CollectorSpec:
    collector_id: str
    source_id: str
    namespace: str
    method: CollectorMethod
    frequency_seconds: int
    freshness_seconds: int
    max_retries: int = 3
    enabled: bool = True
    owner_project: str | None = None
    source_uri: str | None = None
    information_class: InformationClass = InformationClass.INTERNAL

    def __post_init__(self) -> None:
        if not self.collector_id or len(self.collector_id) > 240:
            raise ValueError("collector_id must be non-empty and <= 240 characters")
        if self.frequency_seconds < 60:
            raise ValueError("frequency_seconds must be at least 60")
        if self.freshness_seconds < self.frequency_seconds:
            raise ValueError("freshness_seconds cannot be shorter than frequency_seconds")
        if not 0 <= self.max_retries <= 20:
            raise ValueError("max_retries must be between 0 and 20")


@dataclass
class CollectorState:
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0
    freshness_marker: str | None = None


class CollectorRegistry:
    """Institutional registry that wraps existing collectors without replacing them."""

    def __init__(self) -> None:
        self._specs: dict[str, CollectorSpec] = {}
        self._states: dict[str, CollectorState] = {}

    def register(self, spec: CollectorSpec) -> None:
        current = self._specs.get(spec.collector_id)
        if current is not None and current != spec:
            raise ValueError(
                f"collector_id already registered with different spec: {spec.collector_id}"
            )
        self._specs[spec.collector_id] = spec
        self._states.setdefault(spec.collector_id, CollectorState())

    def spec(self, collector_id: str) -> CollectorSpec:
        try:
            return self._specs[collector_id]
        except KeyError as exc:
            raise KeyError(f"unknown collector: {collector_id}") from exc

    def state(self, collector_id: str) -> CollectorState:
        self.spec(collector_id)
        return self._states[collector_id]

    def due(self, *, now: datetime | None = None) -> tuple[CollectorSpec, ...]:
        current = now or datetime.now(UTC)
        due_specs: list[CollectorSpec] = []
        for collector_id, spec in self._specs.items():
            if not spec.enabled:
                continue
            state = self._states[collector_id]
            reference = state.last_attempt_at or state.last_success_at
            if reference is None or current - reference >= timedelta(seconds=spec.frequency_seconds):
                due_specs.append(spec)
        return tuple(sorted(due_specs, key=lambda item: item.collector_id))

    def record_success(
        self,
        collector_id: str,
        *,
        at: datetime | None = None,
        freshness_marker: str | None = None,
    ) -> None:
        current = at or datetime.now(UTC)
        state = self.state(collector_id)
        state.last_attempt_at = current
        state.last_success_at = current
        state.last_error = None
        state.consecutive_failures = 0
        if freshness_marker is not None:
            state.freshness_marker = freshness_marker

    def record_failure(
        self,
        collector_id: str,
        error: str,
        *,
        at: datetime | None = None,
    ) -> None:
        current = at or datetime.now(UTC)
        state = self.state(collector_id)
        state.last_attempt_at = current
        state.last_error_at = current
        state.last_error = error[:2000]
        state.consecutive_failures += 1

    def health(self, collector_id: str, *, now: datetime | None = None) -> CollectorHealth:
        spec = self.spec(collector_id)
        if not spec.enabled:
            return CollectorHealth.DISABLED
        state = self.state(collector_id)
        if state.last_attempt_at is None:
            return CollectorHealth.UNKNOWN
        if state.last_success_at is None:
            return CollectorHealth.FAILED
        current = now or datetime.now(UTC)
        if current - state.last_success_at > timedelta(seconds=spec.freshness_seconds):
            return CollectorHealth.STALE
        if state.last_error_at and state.last_error_at > state.last_success_at:
            if state.consecutive_failures > spec.max_retries:
                return CollectorHealth.FAILED
            return CollectorHealth.DEGRADED
        return CollectorHealth.HEALTHY

    def snapshot(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = now or datetime.now(UTC)
        collectors: list[dict[str, Any]] = []
        for collector_id in sorted(self._specs):
            spec = self._specs[collector_id]
            state = self._states[collector_id]
            collectors.append(
                {
                    "spec": {
                        **asdict(spec),
                        "method": spec.method.value,
                        "information_class": spec.information_class.value,
                    },
                    "state": {
                        "last_attempt_at": _iso(state.last_attempt_at),
                        "last_success_at": _iso(state.last_success_at),
                        "last_error_at": _iso(state.last_error_at),
                        "last_error": state.last_error,
                        "consecutive_failures": state.consecutive_failures,
                        "freshness_marker": state.freshness_marker,
                    },
                    "health": self.health(collector_id, now=current).value,
                }
            )
        return {
            "schema_version": "1.0",
            "generated_at": current.isoformat(),
            "collectors": collectors,
        }

    def save_atomic(self, path: Path, *, now: datetime | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.snapshot(now=now), ensure_ascii=False, indent=2, sort_keys=True)
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
