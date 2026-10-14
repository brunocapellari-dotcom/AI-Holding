from __future__ import annotations

import subprocess
from contextlib import contextmanager
from pathlib import Path

import pytest

from scripts import backup_local_postgres as recovery

_TABLES = {
    "public.projects": {"rows": 11, "sha256": "a" * 64},
    "public.hermes_event_receipts": {"rows": 25, "sha256": "b" * 64},
}


def _fake_snapshot(monkeypatch) -> None:
    @contextmanager
    def snapshot():
        yield "00000003-0000001B-1", dict(_TABLES)

    monkeypatch.setattr(recovery, "_source_snapshot", snapshot)


def _local(monkeypatch) -> None:
    monkeypatch.setenv("PGDATABASE", "holding")
    monkeypatch.setenv("PGHOST", "127.0.0.1")
    monkeypatch.setenv("HOLDING_BACKUP_HMAC_KEY", "ae" * 32)
    for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR"):
        monkeypatch.delenv(key, raising=False)


def test_signed_postgres_backup_verify_and_tamper_rejection(tmp_path: Path, monkeypatch) -> None:
    _local(monkeypatch)
    _fake_snapshot(monkeypatch)
    calls: list[str] = []

    def fake_run(args, timeout=600):
        calls.append(args[0])
        if args[0] == "pg_dump":
            assert "--snapshot=00000003-0000001B-1" in args
            Path(args[args.index("--file") + 1]).write_bytes(b"PGDMP controlled test archive")
        return subprocess.CompletedProcess(args, 0, "1\n", "")

    monkeypatch.setattr(recovery, "_run", fake_run)
    snapshot = tmp_path / "encrypted-drive" / "backup1"
    with pytest.raises(ValueError, match="encrypted"):
        recovery.backup(snapshot, encrypted_destination_confirmed=False)
    created = recovery.backup(snapshot, encrypted_destination_confirmed=True)
    assert created["status"] == "BACKUP_CREATED"
    verified = recovery.verify(snapshot)
    assert verified["status"] == "VERIFIED"
    assert verified["tables"] == _TABLES
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
    monkeypatch.setattr(
        recovery, "verify", lambda _: {"status": "VERIFIED", "bytes": 12, "tables": _TABLES}
    )
    monkeypatch.setattr(recovery, "_restored_fingerprint", lambda _: dict(_TABLES))
    snapshot = tmp_path / "backup"
    snapshot.mkdir()
    calls = []

    def fake_run(args, timeout=600):
        calls.append(args[0])
        return subprocess.CompletedProcess(args, 0, "1\n" if args[0] == "psql" else "", "")

    monkeypatch.setattr(recovery, "_run", fake_run)
    result = recovery.isolated_restore_drill(snapshot, "holding_restore_test_0002")
    assert result["status"] == "RESTORE_DRILL_PASS"
    assert result["tables_verified"] == 2 and result["rows_verified"] == 36
    assert calls == ["createdb", "pg_restore", "psql", "dropdb"]


def test_restore_drill_fails_and_cleans_up_on_data_mismatch(tmp_path: Path, monkeypatch) -> None:
    _local(monkeypatch)
    monkeypatch.setattr(
        recovery, "verify", lambda _: {"status": "VERIFIED", "bytes": 12, "tables": _TABLES}
    )
    lost_rows = dict(_TABLES)
    lost_rows["public.hermes_event_receipts"] = {"rows": 0, "sha256": "c" * 64}
    monkeypatch.setattr(recovery, "_restored_fingerprint", lambda _: lost_rows)
    snapshot = tmp_path / "backup"
    snapshot.mkdir()
    calls = []

    def fake_run(args, timeout=600):
        calls.append(args[0])
        return subprocess.CompletedProcess(args, 0, "1\n" if args[0] == "psql" else "", "")

    monkeypatch.setattr(recovery, "_run", fake_run)
    with pytest.raises(RuntimeError, match="hermes_event_receipts"):
        recovery.isolated_restore_drill(snapshot, "holding_restore_test_0003")
    assert calls[-1] == "dropdb"


def test_manifest_without_table_fingerprint_is_rejected(tmp_path: Path, monkeypatch) -> None:
    _local(monkeypatch)

    @contextmanager
    def empty_snapshot():
        yield "snap", {}

    monkeypatch.setattr(recovery, "_source_snapshot", empty_snapshot)

    def fake_run(args, timeout=600):
        if args[0] == "pg_dump":
            Path(args[args.index("--file") + 1]).write_bytes(b"PGDMP controlled test archive")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(recovery, "_run", fake_run)
    with pytest.raises(ValueError, match="fingerprint"):
        recovery.backup(tmp_path / "backup", encrypted_destination_confirmed=True)
    assert not (tmp_path / "backup").exists()


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
