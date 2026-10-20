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


def test_migrating_from_empty_creates_current_schema(conn: sqlite3.Connection) -> None:
    migrate(conn)

    assert SCHEMA_VERSION == 2
    assert user_version(conn) == 2
    names = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'index')")
    }
    assert {"transactions", "transactions_height_idx", "daily_prices"} <= names
    conn.rollback()  # the migration was committed, so rolling back now loses nothing
    assert user_version(conn) == 2


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

    assert user_version(conn) == 2
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 1


def test_newer_schema_is_refused(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA user_version = 3")
    conn.commit()

    with pytest.raises(SchemaTooNewError) as excinfo:
        migrate(conn)

    assert excinfo.value.found == 3


# --- schema version 2: daily_prices ---------------------------------------------------------


def insert_price(
    conn: sqlite3.Connection,
    date_utc: str = "2026-10-16",
    usd_price: str = "152.3456",
    status: str = "provisional",
    source: str = "api",
) -> None:
    conn.execute(
        "INSERT INTO daily_prices (date_utc, usd_price, status, source, fetched_at)"
        " VALUES (?, ?, ?, ?, 0)",
        (date_utc, usd_price, status, source),
    )


def test_migrating_a_version_1_database_keeps_its_rows(conn: sqlite3.Connection) -> None:
    migrate(conn, to_version=1)
    insert(conn, occurred_at=1704067200)
    conn.commit()
    assert user_version(conn) == 1

    migrate(conn)

    assert user_version(conn) == 2
    assert conn.execute("SELECT txid, occurred_date FROM transactions").fetchall() == [
        (TXID, "2024-01-01")
    ]
    assert conn.execute("SELECT count(*) FROM daily_prices").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("date_utc", "status", "source"),
    [
        ("2026-1-16", "provisional", "api"),  # GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        ("16-10-2026", "provisional", "api"),
        ("2026-10-16", "pending", "api"),  # status IN ('provisional', 'final')
        ("2026-10-16", "final", "csv"),  # source IN ('api', 'import')
    ],
)
def test_daily_prices_checks_reject_bad_rows(
    conn: sqlite3.Connection, date_utc: str, status: str, source: str
) -> None:
    migrate(conn)

    with pytest.raises(sqlite3.IntegrityError):
        insert_price(conn, date_utc=date_utc, status=status, source=source)


def test_final_price_cannot_be_updated(conn: sqlite3.Connection) -> None:
    migrate(conn)
    insert_price(conn, status="final")
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="final price is immutable"):
        conn.execute("UPDATE daily_prices SET usd_price = '1' WHERE date_utc = '2026-10-16'")


def test_provisional_price_can_be_updated(conn: sqlite3.Connection) -> None:
    migrate(conn)
    insert_price(conn, status="provisional")

    conn.execute(
        "UPDATE daily_prices SET usd_price = '150', status = 'final' WHERE date_utc = '2026-10-16'"
    )

    row = conn.execute("SELECT usd_price, status FROM daily_prices").fetchone()
    assert row == ("150", "final")


@pytest.mark.parametrize("status", ["provisional", "final"])
def test_prices_cannot_be_deleted(conn: sqlite3.Connection, status: str) -> None:
    migrate(conn)
    insert_price(conn, status=status)

    with pytest.raises(sqlite3.IntegrityError, match="prices are never deleted"):
        conn.execute("DELETE FROM daily_prices")
