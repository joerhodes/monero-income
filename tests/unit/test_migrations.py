import sqlite3
from collections.abc import Iterator

import pytest

from monero_income.primitives.errors import SchemaTooNewError
from monero_income.primitives.migrations import SCHEMA_VERSION, migrate

TXID = "a" * 64


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:", autocommit=False)
    yield connection
    connection.close()


def user_version(conn: sqlite3.Connection) -> int:
    version: int = conn.execute("PRAGMA user_version").fetchone()[0]
    return version


def insert(
    conn: sqlite3.Connection,
    txid: str = TXID,
    height: int = 1,
    amount: int = 1,
    occurred_at: int = 0,
) -> None:
    conn.execute(
        "INSERT INTO transactions (txid, height, amount_piconero, occurred_at) VALUES (?, ?, ?, ?)",
        (txid, height, amount, occurred_at),
    )


def test_migrating_from_empty_creates_schema_v1(conn: sqlite3.Connection) -> None:
    migrate(conn)

    assert SCHEMA_VERSION == 1
    assert user_version(conn) == 1
    names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'index')")
    }
    assert {"transactions", "transactions_height_idx"} <= names
    conn.rollback()  # the migration was committed, so rolling back now loses nothing
    assert user_version(conn) == 1


@pytest.mark.parametrize(
    ("txid", "height", "amount"),
    [
        ("a" * 63, 1, 1),  # CHECK (length(txid) = 64)
        (TXID, 0, 1),  # CHECK (height > 0)
        (TXID, 1, 0),  # CHECK (amount_piconero > 0)
    ],
)
def test_checks_reject_bad_rows(
    conn: sqlite3.Connection, txid: str, height: int, amount: int
) -> None:
    migrate(conn)

    with pytest.raises(sqlite3.IntegrityError):
        insert(conn, txid=txid, height=height, amount=amount)


@pytest.mark.parametrize(
    ("occurred_at", "expected_date"),
    [(1704067199, "2023-12-31"), (1704067200, "2024-01-01")],
)
def test_occurred_date_is_utc_calendar_date(
    conn: sqlite3.Connection, occurred_at: int, expected_date: str
) -> None:
    migrate(conn)
    insert(conn, occurred_at=occurred_at)

    row = conn.execute("SELECT occurred_date FROM transactions").fetchone()
    assert row[0] == expected_date


def test_migrating_current_schema_is_a_no_op(conn: sqlite3.Connection) -> None:
    migrate(conn)
    insert(conn)
    conn.commit()

    migrate(conn)

    assert user_version(conn) == 1
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 1


def test_newer_schema_is_refused(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA user_version = 2")
    conn.commit()

    with pytest.raises(SchemaTooNewError) as excinfo:
        migrate(conn)

    assert excinfo.value.found == 2
