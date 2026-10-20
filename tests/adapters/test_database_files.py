import sqlite3
from pathlib import Path

import pytest

from monero_income.primitives.database import insert_records, open_database
from monero_income.primitives.errors import SchemaTooNewError, StorageReadError
from monero_income.primitives.models import TransactionRecord


def user_version(conn: sqlite3.Connection) -> int:
    version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    return version


def test_missing_file_and_directory_are_created(tmp_path: Path) -> None:
    db_path = tmp_path / "missing" / "nested" / "xmr.db"

    conn = open_database(db_path)
    try:
        assert db_path.is_file()
        assert user_version(conn) == 2
    finally:
        conn.close()


def test_existing_database_is_reopened_with_rows_intact(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    stored = TransactionRecord(
        txid="a" * 64, height=10, amount_piconero=123456789012, occurred_at=1_700_000_000
    )
    conn = open_database(db_path)
    insert_records(conn, [stored])
    conn.close()

    conn = open_database(db_path)
    try:
        assert conn.execute(
            "SELECT txid, height, amount_piconero, occurred_at FROM transactions"
        ).fetchall() == [("a" * 64, 10, 123456789012, 1_700_000_000)]
    finally:
        conn.close()


def test_unreadable_file_is_an_error_and_left_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    db_path.write_bytes(b"junk")

    with pytest.raises(StorageReadError):
        open_database(db_path)

    assert db_path.read_bytes() == b"junk"


def test_newer_schema_is_refused(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    raw = sqlite3.connect(db_path)
    raw.execute("PRAGMA user_version = 3")
    raw.commit()
    raw.close()

    with pytest.raises(SchemaTooNewError):
        open_database(db_path)
