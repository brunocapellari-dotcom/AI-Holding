from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import cast

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from second_brain.persistence import ProjectionEvent
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
_SCHEMA_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")


class PostgresKnowledgeStore:
    """Independent append-only PostgreSQL store for institutional knowledge.

    The default schema is deliberately separate from Holding tables. Production should
    use a dedicated Second Brain database/service identity even though integration tests
    may use an isolated schema in a shared ephemeral PostgreSQL instance.
    """

    def __init__(
        self,
        dsn: str,
        *,
        schema: str = "second_brain",
        initialize: bool = False,
    ) -> None:
        if not _SCHEMA_RE.fullmatch(schema):
            raise ValueError("invalid PostgreSQL schema name")
        self.schema = schema
        self.connection = psycopg.connect(_normalize_dsn(dsn), row_factory=dict_row)
        if initialize:
            self.initialize_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "PostgresKnowledgeStore":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del exc_type, exc, traceback
        self.close()

    def initialize_schema(self) -> None:
        schema = sql.Identifier(self.schema)
        statements = [
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema),
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.record_versions (
                    record_id TEXT NOT NULL,
                    version_no INTEGER NOT NULL,
                    record_type TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    information_class TEXT NOT NULL,
                    status TEXT,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    valid_from TIMESTAMPTZ,
                    valid_to TIMESTAMPTZ,
                    known_from TIMESTAMPTZ,
                    known_to TIMESTAMPTZ,
                    recorded_at TIMESTAMPTZ NOT NULL,
                    PRIMARY KEY (record_id, version_no),
                    UNIQUE (record_id, payload_hash)
                )
                """
            ).format(schema),
            sql.SQL(
                "CREATE INDEX IF NOT EXISTS record_versions_namespace_idx "
                "ON {}.record_versions(namespace, record_type, record_id, version_no)"
            ).format(schema),
            sql.SQL(
                "CREATE INDEX IF NOT EXISTS record_versions_temporal_idx "
                "ON {}.record_versions(record_type, valid_from, valid_to, known_from, known_to)"
            ).format(schema),
            sql.SQL(
                """
                CREATE TABLE IF NOT EXISTS {}.projection_outbox (
                    event_id BIGSERIAL PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    version_no INTEGER NOT NULL,
                    target TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    delivered_at TIMESTAMPTZ,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    UNIQUE(record_id, version_no, target),
                    FOREIGN KEY(record_id, version_no)
                        REFERENCES {}.record_versions(record_id, version_no)
                        ON DELETE RESTRICT
                )
                """
            ).format(schema, schema),
            sql.SQL(
                "CREATE INDEX IF NOT EXISTS projection_outbox_pending_idx "
                "ON {}.projection_outbox(target, delivered_at, event_id)"
            ).format(schema),
        ]
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

    def put(self, record: KnowledgeRecord) -> int:
        raw = record.model_dump(mode="json")
        if scan_object_for_secrets(raw):
            raise ValueError("knowledge record rejected: secret-like material detected")
        payload = json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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
        recorded_at = datetime.now(UTC)
        schema = sql.Identifier(self.schema)
        insert_record = sql.SQL(
            """
            INSERT INTO {}.record_versions (
                record_id, version_no, record_type, namespace, information_class,
                status, payload_json, payload_hash, valid_from, valid_to,
                known_from, known_to, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        ).format(schema)
        insert_outbox = sql.SQL(
            """
            INSERT INTO {}.projection_outbox (
                record_id, version_no, target, payload_hash, created_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(record_id, version_no, target) DO NOTHING
            """
        ).format(schema)
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(
                    insert_record,
                    (
                        record.id,
                        version_no,
                        record.record_type,
                        record.namespace,
                        record.information_class.value,
                        status.value if status is not None else None,
                        payload,
                        digest,
                        getattr(temporal, "valid_from", None),
                        getattr(temporal, "valid_to", None),
                        getattr(temporal, "known_from", None),
                        getattr(temporal, "known_to", None),
                        recorded_at,
                    ),
                )
                for target in _projection_targets(record):
                    cursor.execute(insert_outbox, (record.id, version_no, target, digest, recorded_at))
        return version_no

    def get_latest(self, record_id: str) -> KnowledgeRecord | None:
        row = self._latest_row(record_id)
        return self._decode(row) if row is not None else None

    def get_version(self, record_id: str, version_no: int) -> KnowledgeRecord | None:
        query = sql.SQL(
            "SELECT * FROM {}.record_versions WHERE record_id = %s AND version_no = %s"
        ).format(sql.Identifier(self.schema))
        with self.connection.cursor() as cursor:
            cursor.execute(query, (record_id, version_no))
            row = cursor.fetchone()
        return self._decode(row) if row is not None else None

    def history(self, record_id: str) -> tuple[KnowledgeRecord, ...]:
        query = sql.SQL(
            "SELECT * FROM {}.record_versions WHERE record_id = %s ORDER BY version_no ASC"
        ).format(sql.Identifier(self.schema))
        with self.connection.cursor() as cursor:
            cursor.execute(query, (record_id,))
            rows = cursor.fetchall()
        return tuple(self._decode(row) for row in rows)

    def all_latest(self, *, namespace_prefix: str | None = None) -> tuple[KnowledgeRecord, ...]:
        query = sql.SQL(
            """
            SELECT DISTINCT ON (record_id) *
            FROM {}.record_versions
            ORDER BY record_id, version_no DESC
            """
        ).format(sql.Identifier(self.schema))
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
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
        query = sql.SQL(
            """
            SELECT * FROM {}.record_versions
            WHERE record_type = 'Fact'
            ORDER BY record_id ASC, version_no DESC
            """
        ).format(sql.Identifier(self.schema))
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
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
        schema = sql.Identifier(self.schema)
        if target is None:
            query = sql.SQL(
                "SELECT * FROM {}.projection_outbox WHERE delivered_at IS NULL "
                "ORDER BY event_id ASC LIMIT %s"
            ).format(schema)
            params = (limit,)
        else:
            query = sql.SQL(
                "SELECT * FROM {}.projection_outbox WHERE delivered_at IS NULL AND target = %s "
                "ORDER BY event_id ASC LIMIT %s"
            ).format(schema)
            params = (target, limit)
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        return tuple(_decode_projection_event(row) for row in rows)

    def mark_projection_delivered(self, event_id: int) -> None:
        query = sql.SQL(
            "UPDATE {}.projection_outbox SET delivered_at = %s, attempts = attempts + 1, "
            "last_error = NULL WHERE event_id = %s"
        ).format(sql.Identifier(self.schema))
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(query, (datetime.now(UTC), event_id))

    def mark_projection_failed(self, event_id: int, error: str) -> None:
        query = sql.SQL(
            "UPDATE {}.projection_outbox SET attempts = attempts + 1, last_error = %s "
            "WHERE event_id = %s"
        ).format(sql.Identifier(self.schema))
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(query, (error[:2000], event_id))

    def requeue_all_projections(self) -> int:
        rows = self._latest_rows()
        query = sql.SQL(
            """
            INSERT INTO {}.projection_outbox (
                record_id, version_no, target, payload_hash, created_at,
                delivered_at, attempts, last_error
            ) VALUES (%s, %s, %s, %s, %s, NULL, 0, NULL)
            ON CONFLICT(record_id, version_no, target)
            DO UPDATE SET delivered_at = NULL, attempts = 0, last_error = NULL
            """
        ).format(sql.Identifier(self.schema))
        count = 0
        with self.connection.transaction():
            with self.connection.cursor() as cursor:
                for row in rows:
                    record = self._decode(row)
                    for target in _projection_targets(record):
                        cursor.execute(
                            query,
                            (
                                str(row["record_id"]),
                                int(row["version_no"]),
                                target,
                                str(row["payload_hash"]),
                                datetime.now(UTC),
                            ),
                        )
                        count += 1
        return count

    def integrity_check(self) -> bool:
        query = sql.SQL(
            """
            SELECT COUNT(*) AS broken
            FROM {}.projection_outbox o
            LEFT JOIN {}.record_versions r
              ON r.record_id = o.record_id AND r.version_no = o.version_no
            WHERE r.record_id IS NULL
            """
        ).format(sql.Identifier(self.schema), sql.Identifier(self.schema))
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        return row is not None and int(row["broken"]) == 0

    def record_count(self) -> int:
        query = sql.SQL("SELECT COUNT(*) AS count FROM {}.record_versions").format(
            sql.Identifier(self.schema)
        )
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        return int(row["count"]) if row is not None else 0

    def outbox_count(self, *, pending_only: bool = False) -> int:
        condition = sql.SQL(" WHERE delivered_at IS NULL") if pending_only else sql.SQL("")
        query = sql.SQL("SELECT COUNT(*) AS count FROM {}.projection_outbox").format(
            sql.Identifier(self.schema)
        ) + condition
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
        return int(row["count"]) if row is not None else 0

    def _latest_row(self, record_id: str) -> dict[str, object] | None:
        query = sql.SQL(
            "SELECT * FROM {}.record_versions WHERE record_id = %s "
            "ORDER BY version_no DESC LIMIT 1"
        ).format(sql.Identifier(self.schema))
        with self.connection.cursor() as cursor:
            cursor.execute(query, (record_id,))
            return cursor.fetchone()

    def _latest_rows(self) -> list[dict[str, object]]:
        query = sql.SQL(
            "SELECT DISTINCT ON (record_id) * FROM {}.record_versions "
            "ORDER BY record_id, version_no DESC"
        ).format(sql.Identifier(self.schema))
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return list(cursor.fetchall())

    def _decode(self, row: dict[str, object]) -> KnowledgeRecord:
        record_type = str(row["record_type"])
        model = _RECORD_TYPES.get(record_type)
        if model is None:
            raise ValueError(f"unsupported record_type in store: {record_type}")
        parsed = model.model_validate(json.loads(str(row["payload_json"])))
        return cast(KnowledgeRecord, parsed)


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


def _decode_projection_event(row: dict[str, object]) -> ProjectionEvent:
    created = row["created_at"]
    created_at = created if isinstance(created, datetime) else datetime.fromisoformat(str(created))
    return ProjectionEvent(
        event_id=int(row["event_id"]),
        record_id=str(row["record_id"]),
        version_no=int(row["version_no"]),
        target=str(row["target"]),
        payload_hash=str(row["payload_hash"]),
        created_at=created_at,
        attempts=int(row["attempts"]),
        last_error=str(row["last_error"]) if row["last_error"] is not None else None,
    )


def _normalize_dsn(dsn: str) -> str:
    return dsn.replace("postgresql+psycopg://", "postgresql://", 1)


def _namespace_matches(namespace: str, prefix: str) -> bool:
    return namespace == prefix or namespace.startswith(f"{prefix}/")
