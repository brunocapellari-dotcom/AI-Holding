from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from second_brain.ingestion.safety import (
    AntivirusScanner,
    IngestionFinding,
    inspect_file,
    inspect_source_uri,
)


@dataclass(frozen=True)
class RawObservation:
    source_id: str
    source_uri: str | None
    collected_at: str
    filename: str | None
    mime_type: str


@dataclass(frozen=True)
class RawArtifact:
    artifact_id: str
    sha256: str
    size_bytes: int
    content_path: Path
    metadata_path: Path
    findings: tuple[IngestionFinding, ...]


class RawArtifactStore:
    """Content-addressed immutable storage for original ingested bytes."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(
        self,
        content: bytes,
        *,
        source_id: str,
        filename: str | None,
        mime_type: str,
        source_uri: str | None = None,
        collected_at: datetime | None = None,
        antivirus: AntivirusScanner | None = None,
        require_antivirus: bool = False,
    ) -> RawArtifact:
        uri_findings = inspect_source_uri(source_uri) if source_uri else ()
        file_inspection = inspect_file(
            content,
            filename=filename,
            mime_type=mime_type,
            antivirus=antivirus,
            require_antivirus=require_antivirus,
        )
        findings = (*uri_findings, *file_inspection.findings)
        if any(item.severity in {"HIGH", "CRITICAL"} for item in findings):
            codes = ", ".join(item.code for item in findings)
            raise ValueError(f"raw artifact rejected by ingestion policy: {codes}")

        digest = file_inspection.sha256
        shard = self.root / digest[:2]
        shard.mkdir(parents=True, exist_ok=True)
        content_path = shard / f"{digest}.bin"
        metadata_path = shard / f"{digest}.json"
        if content_path.exists():
            existing = content_path.read_bytes()
            if hashlib.sha256(existing).hexdigest() != digest:
                raise RuntimeError(
                    "raw artifact hash mismatch in existing content-addressed store"
                )
            if existing != content:
                raise RuntimeError("content-address collision detected")
        else:
            _atomic_write_bytes(content_path, content)

        observation = RawObservation(
            source_id=source_id,
            source_uri=source_uri,
            collected_at=(collected_at or datetime.now(UTC)).isoformat(),
            filename=filename,
            mime_type=mime_type,
        )
        metadata = _load_metadata(metadata_path, digest, len(content))
        observations = metadata.setdefault("observations", [])
        if not isinstance(observations, list):
            raise RuntimeError("invalid raw artifact observation metadata")
        encoded_observation = asdict(observation)
        if encoded_observation not in observations:
            observations.append(encoded_observation)
        _atomic_write_text(
            metadata_path,
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        return RawArtifact(
            artifact_id=f"raw:sha256:{digest}",
            sha256=digest,
            size_bytes=len(content),
            content_path=content_path,
            metadata_path=metadata_path,
            findings=findings,
        )

    def read(self, sha256: str) -> bytes:
        if not _is_sha256(sha256):
            raise ValueError("invalid sha256")
        path = self.root / sha256[:2] / f"{sha256}.bin"
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != sha256:
            raise RuntimeError("raw artifact integrity check failed")
        return data

    def verify(self, sha256: str) -> bool:
        try:
            self.read(sha256)
        except (FileNotFoundError, RuntimeError, ValueError):
            return False
        return True


def _load_metadata(path: Path, digest: str, size_bytes: int) -> dict[str, object]:
    if not path.exists():
        return {
            "schema_version": "1.0",
            "sha256": digest,
            "size_bytes": size_bytes,
            "observations": [],
        }
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RuntimeError("invalid raw artifact metadata")
    if loaded.get("sha256") != digest or loaded.get("size_bytes") != size_bytes:
        raise RuntimeError("raw artifact metadata integrity mismatch")
    return loaded


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _atomic_write_text(path: Path, content: str) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )
