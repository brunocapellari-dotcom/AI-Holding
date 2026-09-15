from __future__ import annotations

from datetime import datetime
from typing import Protocol, TYPE_CHECKING

from second_brain.schemas import Fact
from second_brain.schemas.contracts import KnowledgeRecord

if TYPE_CHECKING:
    from second_brain.persistence import ProjectionEvent


class KnowledgeStore(Protocol):
    """Minimal canonical-store contract consumed by the Second Brain runtime."""

    def put(self, record: KnowledgeRecord) -> int: ...

    def get_latest(self, record_id: str) -> KnowledgeRecord | None: ...

    def get_version(self, record_id: str, version_no: int) -> KnowledgeRecord | None: ...

    def all_latest(self, *, namespace_prefix: str | None = None) -> tuple[KnowledgeRecord, ...]: ...

    def query_facts_as_of(
        self,
        *,
        valid_at: datetime,
        known_at: datetime,
        namespace_prefix: str | None = None,
    ) -> tuple[Fact, ...]: ...

    def pending_projection_events(
        self,
        *,
        target: str | None = None,
        limit: int = 100,
    ) -> tuple[ProjectionEvent, ...]: ...

    def mark_projection_delivered(self, event_id: int) -> None: ...

    def mark_projection_failed(self, event_id: int, error: str) -> None: ...

    def requeue_all_projections(self) -> int: ...

    def integrity_check(self) -> bool: ...

    def record_count(self) -> int: ...

    def outbox_count(self, *, pending_only: bool = False) -> int: ...
