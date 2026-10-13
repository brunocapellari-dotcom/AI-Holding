from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts import backup_local_postgres as recovery


def _local(monkeypatch) -> None:
    monkeypatch.setenv("PGDATABASE", "holding")
    monkeypatch.setenv("PGHOST", "127.0.0.1")
    monkeypatch.setenv("HOLDING_BACKUP_HMAC_KEY", "ae" * 32)
    for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR"):
        monkeypatch.delenv(key, raising=False)


def test_signed_postgres_backup_verify_and_tamper_rejection(tmp_path: Path, monkeypatch) -> None:
    _local(monkeypatch)
    calls: list[str] = []

    def fake_run(args, timeout=600):
        calls.append(args[0])
        if args[0] == "pg_dump":
            Path(args[args.index("--file") + 1]).write_bytes(b"PGDMP controlled test archive")
        return subprocess.CompletedProcess(args, 0, "1\n", "")

    monkeypatch.setattr(recovery, "_run", fake_run)
    snapshot = tmp_path / "encrypted-drive" / "backup1"
    with pytest.raises(ValueError, match="encrypted"):
        recovery.backup(snapshot, encrypted_destination_confirmed=False)
    created = recovery.backup(snapshot, encrypted_destination_confirmed=True)
    assert created["status"] == "BACKUP_CREATED"
    assert recovery.verify(snapshot)["status"] == "VERIFIED"
    assert "pg_dump" in calls and "pg_restore" in calls
    with pytest.raises(FileExistsError):
        recovery.backup(snapshot, encrypted_destination_confirmed=True)
    (snapshot / "holding.dump").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        recovery.verify(snapshot)


def test_isolated_restore_never_drops_noncreated_database(tmp_path: Path, monkeypatch) -> None:
    _local(monkeypatch)
    monkeypatch.setattr(recovery, "verify", lambda _: {"status": "VERIFIED", "bytes": 12})
    snapshot = tmp_path / "backup"
    snapshot.mkdir()
    calls = []

    def failing_create(args, timeout=600):
        calls.append(args[0])
        if args[0] == "createdb":
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(recovery, "_run", failing_create)
    with pytest.raises(subprocess.CalledProcessError):
        recovery.isolated_restore_drill(snapshot, "holding_restore_test_0001")
    assert calls == ["createdb"]


def test_restore_drill_checks_schema_and_cleans_up(tmp_path: Path, monkeypatch) -> None:
    _local(monkeypatch)
    monkeypatch.setattr(recovery, "verify", lambda _: {"status": "VERIFIED", "bytes": 12})
    snapshot = tmp_path / "backup"
    snapshot.mkdir()
    calls = []

    def fake_run(args, timeout=600):
        calls.append(args[0])
        return subprocess.CompletedProcess(args, 0, "1\n" if args[0] == "psql" else "", "")

    monkeypatch.setattr(recovery, "_run", fake_run)
    result = recovery.isolated_restore_drill(snapshot, "holding_restore_test_0002")
    assert result["status"] == "RESTORE_DRILL_PASS"
    assert calls == ["createdb", "pg_restore", "psql", "dropdb"]


@pytest.mark.parametrize("host", ["192.168.1.9", "db.example.com", "169.254.169.254"])
def test_remote_host_refused(host, monkeypatch) -> None:
    _local(monkeypatch)
    monkeypatch.setenv("PGHOST", host)
    with pytest.raises(ValueError, match="loopback"):
        recovery._assert_local_postgres()


def test_service_override_refused(monkeypatch) -> None:
    _local(monkeypatch)
    monkeypatch.setenv("PGSERVICE", "remote-prod")
    with pytest.raises(ValueError, match="overrides"):
        recovery._assert_local_postgres()
