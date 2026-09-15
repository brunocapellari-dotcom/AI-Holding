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


@dataclass(frozen=True)
class QuarantineArtifact:
    sha256: str
    content_path: Path
    metadata_path: Path
    findings: tuple[IngestionFinding, ...]


class QuarantineStore:
    """Restricted local quarantine for rejected input; never an extraction source."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass

    def put(
        self,
        content: bytes,
        *,
        filename: str | None,
        mime_type: str,
        source_id: str,
        source_uri: str | None,
        findings: tuple[IngestionFinding, ...],
    ) -> QuarantineArtifact:
        digest = hashlib.sha256(content).hexdigest()
        shard = self.root / digest[:2]
        shard.mkdir(parents=True, exist_ok=True, mode=0o700)
        content_path = shard / f"{digest}.quarantine"
        metadata_path = shard / f"{digest}.json"
        if not content_path.exists():
            _atomic_write_bytes(content_path, content, mode=0o600)
        metadata = {
            "schema_version": "1.0",
            "sha256": digest,
            "filename": filename,
            "mime_type": mime_type,
            "source_id": source_id,
            "source_uri": source_uri,
            "quarantined_at": datetime.now(UTC).isoformat(),
            "findings": [asdict(item) for item in findings],
            "extraction_allowed": False,
        }
        _atomic_write_text(
            metadata_path,
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            mode=0o600,
        )
        return QuarantineArtifact(
            sha256=digest,
            content_path=content_path,
            metadata_path=metadata_path,
            findings=findings,
        )


class RawArtifactStore:
    """Content-addressed immutable storage for original ingested bytes."""

    def __init__(
        self,
        root: Path,
        *,
        quarantine: QuarantineStore | None = None,
        antivirus: AntivirusScanner | None = None,
        require_antivirus: bool = False,
        max_bytes: int = 50 * 1024 * 1024,
    ) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.quarantine = quarantine
        self.antivirus = antivirus
        self.require_antivirus = require_antivirus
        self.max_bytes = max_bytes

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
        require_antivirus: bool | None = None,
    ) -> RawArtifact:
        uri_findings = inspect_source_uri(source_uri) if source_uri else ()
        scanner = antivirus if antivirus is not None else self.antivirus
        require_scan = self.require_antivirus if require_antivirus is None else require_antivirus
        file_inspection = inspect_file(
            content,
            filename=filename,
            mime_type=mime_type,
            max_bytes=self.max_bytes,
            antivirus=scanner,
            require_antivirus=require_scan,
        )
        findings = (*uri_findings, *file_inspection.findings)
        if any(item.severity in {"HIGH", "CRITICAL"} for item in findings):
            if self.quarantine is not None:
                self.quarantine.put(
                    content,
                    filename=filename,
                    mime_type=mime_type,
                    source_id=source_id,
                    source_uri=source_uri,
                    findings=findings,
                )
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
                raise RuntimeError("raw artifact hash mismatch in existing content-addressed store")
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


def _atomic_write_bytes(path: Path, content: bytes, *, mode: int = 0o644) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        try:
            os.fchmod(fd, mode)
        except OSError:
            pass
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _atomic_write_text(path: Path, content: str, *, mode: int = 0o644) -> None:
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        try:
            os.fchmod(fd, mode)
        except OSError:
            pass
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
