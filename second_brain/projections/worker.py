from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from second_brain.graph import GraphProjector, build_episode
from second_brain.persistence import ProjectionEvent, SQLiteKnowledgeStore
from second_brain.schemas import Entity, Event, Fact, Relation
from second_brain.schemas.contracts import KnowledgeRecord
from second_brain.vault import write_markdown_atomic

GraphRecord = Fact | Entity | Relation | Event


class ProjectionAdapter(Protocol):
    async def project(self, record: KnowledgeRecord) -> None: ...


class VaultProjectionAdapter:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path

    async def project(self, record: KnowledgeRecord) -> None:
        write_markdown_atomic(self.vault_path, record)


class GraphProjectionAdapter:
    def __init__(self, projector: GraphProjector) -> None:
        self.projector = projector

    async def project(self, record: KnowledgeRecord) -> None:
        if not isinstance(record, (Fact, Entity, Relation, Event)):
            raise TypeError(f"record type is not graph-projectable: {record.record_type}")
        await self.projector.upsert(build_episode(cast(GraphRecord, record)))


@dataclass(frozen=True)
class ProjectionRun:
    attempted: int
    delivered: int
    failed: int
    failures: tuple[str, ...]


class ProjectionWorker:
    """Consumes the transactional outbox without letting derived stores become canonical."""

    def __init__(
        self,
        store: SQLiteKnowledgeStore,
        adapters: dict[str, ProjectionAdapter],
    ) -> None:
        self.store = store
        self.adapters = dict(adapters)

    async def run_once(self, *, limit: int = 100) -> ProjectionRun:
        events = self.store.pending_projection_events(limit=limit)
        failures: list[str] = []
        delivered = 0
        for event in events:
            failure = await self._deliver(event)
            if failure is None:
                delivered += 1
            else:
                failures.append(failure)
        return ProjectionRun(
            attempted=len(events),
            delivered=delivered,
            failed=len(failures),
            failures=tuple(failures),
        )

    async def drain(self, *, batch_size: int = 200, max_batches: int = 1000) -> ProjectionRun:
        if batch_size < 1 or batch_size > 10_000:
            raise ValueError("batch_size must be between 1 and 10000")
        if max_batches < 1 or max_batches > 100_000:
            raise ValueError("max_batches must be between 1 and 100000")
        attempted = 0
        delivered = 0
        failures: list[str] = []
        for _ in range(max_batches):
            run = await self.run_once(limit=batch_size)
            attempted += run.attempted
            delivered += run.delivered
            failures.extend(run.failures)
            if run.attempted == 0 or run.failed:
                break
        return ProjectionRun(
            attempted=attempted,
            delivered=delivered,
            failed=len(failures),
            failures=tuple(failures),
        )

    async def _deliver(self, event: ProjectionEvent) -> str | None:
        adapter = self.adapters.get(event.target)
        if adapter is None:
            message = f"projection target has no adapter: {event.target}"
            self.store.mark_projection_failed(event.event_id, message)
            return message
        record = self.store.get_version(event.record_id, event.version_no)
        if record is None:
            message = f"projection record not found: {event.record_id}@{event.version_no}"
            self.store.mark_projection_failed(event.event_id, message)
            return message
        try:
            await adapter.project(record)
        except Exception as exc:  # noqa: BLE001 - boundary records failure and retries later.
            message = f"{event.target}:{event.record_id}@{event.version_no}: {exc}"
            self.store.mark_projection_failed(event.event_id, message)
            return message
        self.store.mark_projection_delivered(event.event_id)
        return None
