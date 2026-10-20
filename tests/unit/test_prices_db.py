import sqlite3
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

import pytest

from monero_income.primitives.database import insert_records
from monero_income.primitives.errors import StorageWriteError
from monero_income.primitives.migrations import migrate
from monero_income.primitives.models import DailyPrice, PriceNeed, TransactionRecord
from monero_income.primitives.prices_db import (
    all_days_final,
    insert_imported,
    price_needs,
    priced_days,
    upsert_price,
)

D1 = date(2026, 10, 14)
D2 = date(2026, 10, 15)
D3 = date(2026, 10, 16)


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:", autocommit=False)
    migrate(connection)
    yield connection
    connection.close()


def noon(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp())


def add_transactions(conn: sqlite3.Connection, *days: date) -> None:
    insert_records(
        conn,
        [
            TransactionRecord(
                txid=f"{index:064x}", height=index + 1, amount_piconero=1, occurred_at=noon(day)
            )
            for index, day in enumerate(days)
        ],
    )


def price(
    day: date,
    usd: str = "152.3456",
    status: Literal["provisional", "final"] = "final",
    source: Literal["api", "import"] = "api",
) -> DailyPrice:
    return DailyPrice(
        date_utc=day, usd_price=Decimal(usd), status=status, source=source, fetched_at=1
    )


def stored(conn: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    return conn.execute(
        "SELECT date_utc, usd_price, status, source FROM daily_prices ORDER BY date_utc"
    ).fetchall()


def test_price_needs_lists_transaction_days_without_a_final_price(
    conn: sqlite3.Connection,
) -> None:
    add_transactions(conn, D3, D1, D1, D2)  # two transactions on D1
    upsert_price(conn, price(D2, status="final"))
    upsert_price(conn, price(D3, status="provisional"))

    assert price_needs(conn) == [
        PriceNeed(date_utc=D1, has_provisional=False),
        PriceNeed(date_utc=D3, has_provisional=True),
    ]


def test_price_needs_is_empty_without_transactions(conn: sqlite3.Connection) -> None:
    upsert_price(conn, price(D1, status="provisional"))

    assert price_needs(conn) == []


def test_upsert_inserts_and_commits(conn: sqlite3.Connection) -> None:
    upsert_price(conn, price(D1, status="provisional"))
    conn.rollback()  # nothing pending: the upsert committed

    assert stored(conn) == [("2026-10-14", "152.3456", "provisional", "api")]


def test_upsert_replaces_a_provisional_price(conn: sqlite3.Connection) -> None:
    upsert_price(conn, price(D1, "150", status="provisional"))

    upsert_price(conn, price(D1, "151.5", status="final"))

    assert stored(conn) == [("2026-10-14", "151.5", "final", "api")]


def test_upsert_leaves_a_final_price_unchanged(conn: sqlite3.Connection) -> None:
    upsert_price(conn, price(D1, "150", status="final"))

    upsert_price(conn, price(D1, "999", status="final"))
    upsert_price(conn, price(D1, "999", status="provisional"))

    assert stored(conn) == [("2026-10-14", "150", "final", "api")]


def test_priced_days_returns_requested_days_with_any_price(conn: sqlite3.Connection) -> None:
    upsert_price(conn, price(D1, status="final"))
    upsert_price(conn, price(D2, status="provisional"))

    assert priced_days(conn, [D1, D2, D3]) == {D1, D2}
    assert priced_days(conn, []) == set()


def test_insert_imported_is_one_transaction(conn: sqlite3.Connection) -> None:
    insert_imported(conn, [price(D1, source="import"), price(D2, source="import")])
    conn.rollback()

    assert [row[0] for row in stored(conn)] == ["2026-10-14", "2026-10-15"]


def test_insert_imported_rolls_back_everything_on_a_conflict(conn: sqlite3.Connection) -> None:
    upsert_price(conn, price(D2, "150", status="provisional"))

    with pytest.raises(StorageWriteError):
        insert_imported(conn, [price(D1, source="import"), price(D2, source="import")])

    assert stored(conn) == [("2026-10-15", "150", "provisional", "api")]


def test_all_days_final(conn: sqlite3.Connection) -> None:
    assert not all_days_final(conn)  # no transactions recorded: never "all valued"

    add_transactions(conn, D1, D2)
    upsert_price(conn, price(D1, status="final"))
    assert not all_days_final(conn)

    upsert_price(conn, price(D2, status="provisional"))
    assert not all_days_final(conn)

    upsert_price(conn, price(D2, status="final"))
    assert all_days_final(conn)


@pytest.mark.parametrize(
    "usd", ["152.3456", "0.000000012345678901234567890123", "123456789012345678901234.5"]
)
def test_prices_round_trip_exactly_without_exponents(conn: sqlite3.Connection, usd: str) -> None:
    upsert_price(conn, price(D1, usd))

    text = stored(conn)[0][1]
    assert "E" not in text.upper()
    assert Decimal(text) == Decimal(usd)
    assert text == usd


def test_exponent_form_is_stored_as_plain_decimal(conn: sqlite3.Connection) -> None:
    upsert_price(conn, price(D1, "1.5E+2"))

    assert stored(conn)[0][1] == "150"
