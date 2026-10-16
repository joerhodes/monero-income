import sqlite3
from collections.abc import Iterator

import pytest

from monero_income.primitives.database import (
    insert_records,
    last_recorded_height,
    recorded_txids,
)
from monero_income.primitives.errors import StorageWriteError
from monero_income.primitives.migrations import migrate
from monero_income.primitives.models import TransactionRecord

SQLITE_INTEGER_MAX = 9_223_372_036_854_775_807


def record(seed: str, height: int = 100, amount: int = 1_000_000_000_000) -> TransactionRecord:
    return TransactionRecord(
        txid=seed * 64, height=height, amount_piconero=amount, occurred_at=1_700_000_000
    )


def rows(conn: sqlite3.Connection) -> list[tuple[object, ...]]:
    return conn.execute(
        "SELECT txid, height, amount_piconero, occurred_at FROM transactions ORDER BY txid"
    ).fetchall()


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:", autocommit=False)
    migrate(connection)
    yield connection
    connection.close()


def test_last_recorded_height(conn: sqlite3.Connection) -> None:
    assert last_recorded_height(conn) is None

    insert_records(conn, [record("a", height=5), record("b", height=42), record("c", height=7)])

    assert last_recorded_height(conn) == 42


def test_recorded_txids_returns_only_existing_requested_ids(conn: sqlite3.Connection) -> None:
    insert_records(conn, [record("a"), record("b")])

    assert recorded_txids(conn, ["a" * 64, "c" * 64]) == {"a" * 64}
    assert recorded_txids(conn, []) == set()


def test_insert_records_commits(conn: sqlite3.Connection) -> None:
    batch = [record("a", amount=123456789012), record("b")]

    insert_records(conn, batch)
    conn.rollback()  # nothing pending: the batch was already committed

    assert rows(conn) == [
        ("a" * 64, 100, 123456789012, 1_700_000_000),
        ("b" * 64, 100, 1_000_000_000_000, 1_700_000_000),
    ]


def test_duplicate_txid_rolls_back_the_whole_batch(conn: sqlite3.Connection) -> None:
    with pytest.raises(StorageWriteError):
        insert_records(conn, [record("a"), record("b"), record("a")])

    assert rows(conn) == []


def test_amount_too_large_for_sqlite_is_a_write_error(conn: sqlite3.Connection) -> None:
    with pytest.raises(StorageWriteError):
        insert_records(conn, [record("a"), record("b", amount=SQLITE_INTEGER_MAX + 1)])

    assert rows(conn) == []


def test_existing_rows_are_never_updated(conn: sqlite3.Connection) -> None:
    insert_records(conn, [record("a", height=10, amount=5)])

    with pytest.raises(StorageWriteError):
        insert_records(conn, [record("a", height=11, amount=6)])

    assert rows(conn) == [("a" * 64, 10, 5, 1_700_000_000)]
