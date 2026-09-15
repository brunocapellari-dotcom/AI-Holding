from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from second_brain.schemas import (
    Claim,
    Decision,
    Document,
    Entity,
    Evaluation,
    Event,
    Evidence,
    Fact,
    Learning,
    LifecycleStatus,
    Method,
    Model,
    Observation,
    Relation,
    Skill,
    Source,
)
from second_brain.schemas.contracts import KnowledgeRecord
from second_brain.security import (
    allow_graph_projection,
    allow_standard_vault_export,
    scan_object_for_secrets,
)
from second_brain.temporal import visible_as_of

_RECORD_TYPES: dict[str, type[KnowledgeRecord]] = {
    "Source": Source,
    "Document": Document,
    "Observation": Observation,
    "Evidence": Evidence,
    "Claim": Claim,
    "Fact": Fact,
    "Entity": Entity,
    "Relation": Relation,
    "Event": Event,
    "Method": Method,
    "Model": Model,
    "Skill": Skill,
    "Decision": Decision,
    "Evaluation": Evaluation,
    "Learning": Learning,
}
_IMMUTABLE_ORIGINAL_TYPES = {"Document", "Evidence"}


@dataclass(frozen=True)
class ProjectionEvent:
    event_id: int
    record_id: str
    version_no: int
    target: str
    payload_hash: str
    created_at: datetime
    attempts: int
    last_error: str | None


class SQLiteKnowledgeStore:
    """Append-only portable reference store with transactional projection outbox."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SQLiteKnowledgeStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback
        self.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS record_versions (
                record_id TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                record_type TEXT NOT NULL,
                namespace TEXT NOT NULL,
                information_class TEXT NOT NULL,
                status TEXT,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                valid_from TEXT,
                valid_to TEXT,
                known_from TEXT,
                known_to TEXT,
                recorded_at TEXT NOT NULL,
                PRIMARY KEY (record_id, version_no),
                UNIQUE (record_id, payload_hash)
            );
            CREATE INDEX IF NOT EXISTS idx_record_versions_namespace
                ON record_versions(namespace, record_type, record_id, version_no);
            CREATE INDEX IF NOT EXISTS idx_record_versions_temporal
                ON record_versions(record_type, valid_from, valid_to, known_from, known_to);

            CREATE TABLE IF NOT EXISTS projection_outbox (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                target TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                delivered_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                UNIQUE(record_id, version_no, target),
                FOREIGN KEY(record_id, version_no)
                    REFERENCES record_versions(record_id, version_no)
                    ON DELETE RESTRICT
            );
            CREATE INDEX IF NOT EXISTS idx_projection_outbox_pending
                ON projection_outbox(target, delivered_at, event_id);
            """
        )
        self.connection.commit()

    def put(self, record: KnowledgeRecord) -> int:
        raw = record.model_dump(mode="json")
        if scan_object_for_secrets(raw):
            raise ValueError("knowledge record rejected: secret-like material detected")
        payload = json.dumps(
            raw,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        latest = self._latest_row(record.id)
        if latest is not None:
            if str(latest["payload_hash"]) == digest:
                return int(latest["version_no"])
            if record.record_type in _IMMUTABLE_ORIGINAL_TYPES:
                raise ValueError(f"{record.record_type} originals are immutable; use a new stable id")
            version_no = int(latest["version_no"]) + 1
        else:
            version_no = 1

        temporal = getattr(record, "temporal", None)
        status = getattr(record, "status", None)
        recorded_at = datetime.now(UTC).isoformat()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO record_versions (
                    record_id, version_no, record_type, namespace, information_class,
                    status, payload_json, payload_hash, valid_from, valid_to,
                    known_from, known_to, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    version_no,
                    record.record_type,
                    record.namespace,
                    record.information_class.value,
                    status.value if status is not None else None,
                    payload,
                    digest,
                    _iso(getattr(temporal, "valid_from", None)),
                    _iso(getattr(temporal, "valid_to", None)),
                    _iso(getattr(temporal, "known_from", None)),
                    _iso(getattr(temporal, "known_to", None)),
                    recorded_at,
                ),
            )
            for target in _projection_targets(record):
                self.connection.execute(
                    """
                    INSERT OR IGNORE INTO projection_outbox (
                        record_id, version_no, target, payload_hash, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (record.id, version_no, target, digest, recorded_at),
                )
        return version_no

    def get_latest(self, record_id: str) -> KnowledgeRecord | None:
        row = self._latest_row(record_id)
        return self._decode(row) if row is not None else None

    def get_version(self, record_id: str, version_no: int) -> KnowledgeRecord | None:
        row = self.connection.execute(
            """
            SELECT * FROM record_versions
            WHERE record_id = ? AND version_no = ?
            """,
            (record_id, version_no),
        ).fetchone()
        return self._decode(row) if row is not None else None

    def history(self, record_id: str) -> tuple[KnowledgeRecord, ...]:
        rows = self.connection.execute(
            "SELECT * FROM record_versions WHERE record_id = ? ORDER BY version_no ASC",
            (record_id,),
        ).fetchall()
        return tuple(self._decode(row) for row in rows)

    def all_latest(self, *, namespace_prefix: str | None = None) -> tuple[KnowledgeRecord, ...]:
        rows = self.connection.execute(
            """
            SELECT rv.*
            FROM record_versions rv
            JOIN (
                SELECT record_id, MAX(version_no) AS version_no
                FROM record_versions
                GROUP BY record_id
            ) latest
              ON rv.record_id = latest.record_id AND rv.version_no = latest.version_no
            ORDER BY rv.record_id
            """
        ).fetchall()
        records = tuple(self._decode(row) for row in rows)
        if namespace_prefix is None:
            return records
        return tuple(
            record for record in records if _namespace_matches(record.namespace, namespace_prefix)
        )

    def query_facts_as_of(
        self,
        *,
        valid_at: datetime,
        known_at: datetime,
        namespace_prefix: str | None = None,
    ) -> tuple[Fact, ...]:
        rows = self.connection.execute(
            """
            SELECT * FROM record_versions
            WHERE record_type = 'Fact'
            ORDER BY record_id ASC, version_no DESC
            """
        ).fetchall()
        result: list[Fact] = []
        seen: set[str] = set()
        for row in rows:
            record = self._decode(row)
            if not isinstance(record, Fact) or record.id in seen:
                continue
            if namespace_prefix and not _namespace_matches(record.namespace, namespace_prefix):
                continue
            if visible_as_of(record, valid_at=valid_at, known_at=known_at):
                result.append(record)
                seen.add(record.id)
        return tuple(result)

    def pending_projection_events(
        self,
        *,
        target: str | None = None,
        limit: int = 100,
    ) -> tuple[ProjectionEvent, ...]:
        if limit < 1 or limit > 10_000:
            raise ValueError("limit must be between 1 and 10000")
        if target is None:
            rows = self.connection.execute(
                """
                SELECT * FROM projection_outbox
                WHERE delivered_at IS NULL
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                """
                SELECT * FROM projection_outbox
                WHERE delivered_at IS NULL AND target = ?
                ORDER BY event_id ASC
                LIMIT ?
                """,
                (target, limit),
            ).fetchall()
        return tuple(_decode_projection_event(row) for row in rows)

    def mark_projection_delivered(self, event_id: int) -> None:
        with self.connection:
            self.connection.execute(
                """
                UPDATE projection_outbox
                SET delivered_at = ?, attempts = attempts + 1, last_error = NULL
                WHERE event_id = ?
                """,
                (datetime.now(UTC).isoformat(), event_id),
            )

    def mark_projection_failed(self, event_id: int, error: str) -> None:
        with self.connection:
            self.connection.execute(
                """
                UPDATE projection_outbox
                SET attempts = attempts + 1, last_error = ?
                WHERE event_id = ?
                """,
                (error[:2000], event_id),
            )

    def requeue_all_projections(self) -> int:
        """Rebuild the derived surfaces from append-only institutional records."""
        count = 0
        rows = self.connection.execute(
            """
            SELECT rv.*
            FROM record_versions rv
            JOIN (
                SELECT record_id, MAX(version_no) AS version_no
                FROM record_versions
                GROUP BY record_id
            ) latest
              ON rv.record_id = latest.record_id AND rv.version_no = latest.version_no
            ORDER BY rv.record_id
            """
        ).fetchall()
        now = datetime.now(UTC).isoformat()
        with self.connection:
            for row in rows:
                record = self._decode(row)
                for target in _projection_targets(record):
                    cursor = self.connection.execute(
                        """
                        INSERT INTO projection_outbox (
                            record_id, version_no, target, payload_hash, created_at,
                            delivered_at, attempts, last_error
                        ) VALUES (?, ?, ?, ?, ?, NULL, 0, NULL)
                        ON CONFLICT(record_id, version_no, target)
                        DO UPDATE SET delivered_at = NULL, attempts = 0, last_error = NULL
                        """,
                        (
                            str(row["record_id"]),
                            int(row["version_no"]),
                            target,
                            str(row["payload_hash"]),
                            now,
                        ),
                    )
                    count += max(cursor.rowcount, 0)
        return count

    def integrity_check(self) -> bool:
        result = self.connection.execute("PRAGMA integrity_check").fetchone()
        return result is not None and str(result[0]).lower() == "ok"

    def backup_to(self, destination: str | Path) -> None:
        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(target_path)
        try:
            self.connection.backup(target)
        finally:
            target.close()

    def record_count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM record_versions").fetchone()
        return int(row[0]) if row is not None else 0

    def outbox_count(self, *, pending_only: bool = False) -> int:
        sql = "SELECT COUNT(*) FROM projection_outbox"
        if pending_only:
            sql += " WHERE delivered_at IS NULL"
        row = self.connection.execute(sql).fetchone()
        return int(row[0]) if row is not None else 0

    def _latest_row(self, record_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            """
            SELECT * FROM record_versions
            WHERE record_id = ?
            ORDER BY version_no DESC
            LIMIT 1
            """,
            (record_id,),
        ).fetchone()

    def _decode(self, row: sqlite3.Row) -> KnowledgeRecord:
        record_type = str(row["record_type"])
        model = _RECORD_TYPES.get(record_type)
        if model is None:
            raise ValueError(f"unsupported record_type in store: {record_type}")
        parsed = model.model_validate(json.loads(str(row["payload_json"])))
        return cast(KnowledgeRecord, parsed)


def load_records(store: SQLiteKnowledgeStore, records: Iterable[KnowledgeRecord]) -> None:
    for record in records:
        store.put(record)


def _projection_targets(record: KnowledgeRecord) -> tuple[str, ...]:
    targets: list[str] = []
    if allow_standard_vault_export(record.information_class):
        targets.append("vault")
    if allow_graph_projection(record.information_class) and _graph_eligible(record):
        targets.append("graphiti")
    return tuple(targets)


def _graph_eligible(record: KnowledgeRecord) -> bool:
    if isinstance(record, Fact):
        return record.status in {LifecycleStatus.CANONICO, LifecycleStatus.SUPERADO}
    if isinstance(record, (Relation, Event)):
        return record.status in {
            LifecycleStatus.VALIDADO,
            LifecycleStatus.CANONICO,
            LifecycleStatus.SUPERADO,
        }
    return isinstance(record, Entity)


def _decode_projection_event(row: sqlite3.Row) -> ProjectionEvent:
    return ProjectionEvent(
        event_id=int(row["event_id"]),
        record_id=str(row["record_id"]),
        version_no=int(row["version_no"]),
        target=str(row["target"]),
        payload_hash=str(row["payload_hash"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        attempts=int(row["attempts"]),
        last_error=str(row["last_error"]) if row["last_error"] is not None else None,
    )


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _namespace_matches(namespace: str, prefix: str) -> bool:
    return namespace == prefix or namespace.startswith(f"{prefix}/")
