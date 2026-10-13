"""Local PostgreSQL backup and isolated restore drill for AI Holding.

Runs standard PostgreSQL CLI tools; no GitHub runner or GCP account required.
The destination must be on an operator-confirmed encrypted filesystem.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_RESTORE_NAME = re.compile(r"^holding_restore_[a-z0-9_]{4,40}$")


def _key() -> bytes:
    raw = os.getenv("HOLDING_BACKUP_HMAC_KEY", "")
    try:
        value = bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError("invalid HMAC key encoding") from exc
    if len(value) < 32:
        raise ValueError("HOLDING_BACKUP_HMAC_KEY must be >=32 bytes")
    return value


def _run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    # Shell is always disabled. Passwords are read by libpq from authorized local
    # environment or pgpass; no credentials are passed in command arguments.
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=timeout)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for part in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _encode(record: dict[str, Any]) -> bytes:
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def backup(destination: str | Path, *, encrypted_destination_confirmed: bool) -> dict[str, object]:
    if not encrypted_destination_confirmed:
        raise ValueError("an encrypted destination must be confirmed")
    key = _key()
    dest = Path(destination).resolve()
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("backup directory already exists")
    staging = dest.with_name(f".{dest.name}.staging-{uuid.uuid4().hex}")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        archive = staging / "holding.dump"
        _run(["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", str(archive)])
        if not archive.is_file() or archive.stat().st_size == 0:
            raise RuntimeError("pg_dump produced no archive")
        _run(["pg_restore", "--list", str(archive)])
        manifest = {
            "kind": "HOLDING_LOCAL_POSTGRES_BACKUP",
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "archive": "holding.dump",
            "bytes": archive.stat().st_size,
            "sha256": _hash(archive),
            "encrypted_destination_operator_confirmed": True,
        }
        payload = _encode(manifest)
        (staging / "manifest.json").write_bytes(payload)
        (staging / "manifest.hmac").write_text(
            hmac.new(key, payload, hashlib.sha256).hexdigest() + "\n", encoding="ascii"
        )
        verify(staging)
        staging.rename(dest)
        return {"status": "BACKUP_CREATED", "destination": str(dest), "bytes": manifest["bytes"]}
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def verify(snapshot: str | Path) -> dict[str, object]:
    key = _key()
    if Path(snapshot).is_symlink():
        raise ValueError("symlink snapshot rejected")
    base = Path(snapshot).resolve(strict=True)
    if not base.is_dir():
        raise ValueError("snapshot is not a directory")
    for name in ("manifest.json", "manifest.hmac", "holding.dump"):
        path = base / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("incomplete or unsafe backup")
    payload = (base / "manifest.json").read_bytes()
    actual = hmac.new(key, payload, hashlib.sha256).hexdigest()
    signed = (base / "manifest.hmac").read_text(encoding="ascii").strip()
    if not hmac.compare_digest(actual, signed):
        raise ValueError("manifest HMAC verification failed")
    manifest = json.loads(payload)
    if manifest.get("kind") != "HOLDING_LOCAL_POSTGRES_BACKUP" or manifest.get("version") != 1:
        raise ValueError("wrong backup format")
    archive = base / "holding.dump"
    if archive.stat().st_size != manifest.get("bytes") or _hash(archive) != manifest.get("sha256"):
        raise ValueError("archive checksum mismatch")
    if {p.name for p in base.iterdir()} != {"manifest.json", "manifest.hmac", "holding.dump"}:
        raise ValueError("unexpected snapshot content")
    _run(["pg_restore", "--list", str(archive)])
    return {"status": "VERIFIED", "bytes": archive.stat().st_size}


def isolated_restore_drill(snapshot: str | Path, target_db: str) -> dict[str, object]:
    if not _RESTORE_NAME.fullmatch(target_db):
        raise ValueError("restore database name must match holding_restore_*")
    if target_db == os.getenv("PGDATABASE", ""):
        raise ValueError("restore cannot target production database")
    verified = verify(snapshot)
    archive = Path(snapshot).resolve(strict=True) / "holding.dump"
    created = False
    try:
        _run(["createdb", "--template", "template0", target_db])
        created = True
        _run(["pg_restore", "--exit-on-error", "--single-transaction", "--no-owner",
              "--no-acl", "--dbname", target_db, str(archive)], timeout=1200)
        result = _run(["psql", "--dbname", target_db, "--no-psqlrc", "--tuples-only",
                       "--no-align", "--command",
                       "SELECT CASE WHEN to_regclass('public.projects') IS NOT NULL THEN 1 ELSE 0 END"])
        if result.stdout.strip() != "1":
            raise RuntimeError("restored Holding schema missing projects table")
        return {"status": "RESTORE_DRILL_PASS", "archive_bytes": verified["bytes"], "cleaned_up": True}
    finally:
        if created:
            # Never drop an existing or operator-selected production DB:
            # the target was just created by this routine with a strict name.
            _run(["dropdb", "--if-exists", target_db])


def main() -> int:
    parser = argparse.ArgumentParser(description="Holding zero-cost PostgreSQL recovery")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("backup")
    create.add_argument("--destination", required=True)
    create.add_argument("--encrypted-destination-confirmed", action="store_true")
    check = commands.add_parser("verify")
    check.add_argument("--snapshot", required=True)
    restore = commands.add_parser("restore-drill")
    restore.add_argument("--snapshot", required=True)
    restore.add_argument("--target-db", required=True)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            result = backup(args.destination, encrypted_destination_confirmed=args.encrypted_destination_confirmed)
        elif args.command == "verify":
            result = verify(args.snapshot)
        else:
            result = isolated_restore_drill(args.snapshot, args.target_db)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": type(exc).__name__}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
