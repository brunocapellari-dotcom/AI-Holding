from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from second_brain.schemas import Entity, Event, Fact, LifecycleStatus, Relation
from second_brain.security import allow_graph_projection, scan_object_for_secrets

GraphSource = Fact | Entity | Relation | Event


@dataclass(frozen=True)
class GraphEpisode:
    episode_id: str
    group_id: str
    record_id: str
    record_type: str
    payload: dict[str, object]
    content_hash: str


class GraphProjector(Protocol):
    async def upsert(self, episode: GraphEpisode) -> None: ...


def _safe_group_id(namespace: str) -> str:
    return namespace.replace("/", "__").replace(".", "_")[:120]


def build_episode(record: GraphSource) -> GraphEpisode:
    if isinstance(record, Fact) and record.status not in {
        LifecycleStatus.CANONICO,
        LifecycleStatus.SUPERADO,
    }:
        raise ValueError("only institutional facts may be projected")
    if isinstance(record, (Relation, Event)) and record.status not in {
        LifecycleStatus.VALIDADO,
        LifecycleStatus.CANONICO,
        LifecycleStatus.SUPERADO,
    }:
        raise ValueError("unvalidated graph records may not be projected")
    if not allow_graph_projection(record.information_class):
        raise PermissionError("information classification is not allowed in the shared graph")

    payload = record.model_dump(mode="json")
    if scan_object_for_secrets(payload):
        raise ValueError("graph projection blocked by secret scanner")

    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    content_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return GraphEpisode(
        episode_id=f"{record.id}:{content_hash[:16]}",
        group_id=_safe_group_id(record.namespace),
        record_id=record.id,
        record_type=record.record_type,
        payload=payload,
        content_hash=content_hash,
    )
