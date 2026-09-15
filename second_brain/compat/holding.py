from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from second_brain.lifecycle import LEGACY_LIFECYCLE_MAP
from second_brain.schemas import LifecycleStatus


@dataclass(frozen=True)
class LegacyKnowledgeSnapshot:
    legacy_id: str
    namespace: str
    statement: str
    status: LifecycleStatus
    confidence: float
    source_name: str
    source_uri: str | None
    raw: Mapping[str, Any]


def adapt_legacy_holding_claim(payload: Mapping[str, Any]) -> LegacyKnowledgeSnapshot:
    lifecycle = str(payload.get("lifecycle_status", "raw"))
    if lifecycle not in LEGACY_LIFECYCLE_MAP:
        raise ValueError(f"unknown legacy lifecycle: {lifecycle}")
    confidence_raw = float(payload.get("confidence", 50))
    confidence = confidence_raw / 100 if confidence_raw > 1 else confidence_raw
    return LegacyKnowledgeSnapshot(
        legacy_id=str(payload["id"]),
        namespace=str(payload.get("namespace") or "shared"),
        statement=str(payload["statement"]),
        status=LEGACY_LIFECYCLE_MAP[lifecycle],
        confidence=min(max(confidence, 0.0), 1.0),
        source_name=str(payload.get("source_name") or "legacy-holding"),
        source_uri=str(payload["source_uri"]) if payload.get("source_uri") else None,
        raw=payload,
    )
