"""export_records: one read-only join of transactions to their UTC day's price."""

import sqlite3
from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

import pytest

from monero_income.primitives.database import insert_records, open_database
from monero_income.primitives.export_db import export_records
from monero_income.primitives.models import DailyPrice, ExportRecord, TransactionRecord
from monero_income.primitives.prices_db import insert_imported, upsert_price

D1, D2, D3 = date(2026, 10, 14), date(2026, 10, 15), date(2026, 10, 16)
FETCHED = int(datetime(2026, 10, 17, 12, tzinfo=UTC).timestamp())


def at(day: date, hour: int = 12) -> int:
    return int(datetime(day.year, day.month, day.day, hour, tzinfo=UTC).timestamp())


def tx(seed: str, day: date, hour: int = 12, height: int = 100) -> TransactionRecord:
    return TransactionRecord(seed * 64, height, 1_000_000_000_000, at(day, hour))


def price(day: date, text: str, status: Literal["provisional", "final"] = "final") -> DailyPrice:
    return DailyPrice(day, Decimal(text), status, "api", FETCHED)


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = open_database(tmp_path / "x.db")
    yield connection
    connection.close()


def by_txid(conn: sqlite3.Connection) -> dict[str, ExportRecord]:
    return {record.txid: record for record in export_records(conn)}


def test_each_transaction_gets_its_days_price_and_status(conn: sqlite3.Connection) -> None:
    insert_records(conn, [tx("a", D1), tx("b", D2), tx("c", D3)])
    upsert_price(conn, price(D1, "152.3456"))
    upsert_price(conn, price(D2, "160.5", "provisional"))

    records = by_txid(conn)

    assert records["a" * 64] == ExportRecord(
        "a" * 64, 100, 1_000_000_000_000, at(D1), Decimal("152.3456"), "final"
    )
    assert (records["b" * 64].usd_price, records["b" * 64].price_status) == (
        Decimal("160.5"),
        "provisional",
    )
    assert (records["c" * 64].usd_price, records["c" * 64].price_status) == (None, None)


def test_transactions_on_one_day_share_its_price(conn: sqlite3.Connection) -> None:
    insert_records(conn, [tx("a", D1, hour=0, height=100), tx("b", D1, hour=23, height=101)])
    upsert_price(conn, price(D1, "152.3456"))

    assert {r.usd_price for r in export_records(conn)} == {Decimal("152.3456")}


@pytest.mark.parametrize("text", ["150", "163.40000000000001"])
def test_stored_price_text_reads_back_exactly(conn: sqlite3.Connection, text: str) -> None:
    insert_records(conn, [tx("a", D1)])
    insert_imported(conn, [DailyPrice(D1, Decimal(text), "final", "import", FETCHED)])

    (record,) = export_records(conn)

    assert record.usd_price == Decimal(text)
    assert format(record.usd_price, "f") == text  # same digits, not only an equal value


def test_empty_database_gives_no_records(conn: sqlite3.Connection) -> None:
    assert export_records(conn) == []


def test_reading_changes_nothing(conn: sqlite3.Connection) -> None:
    insert_records(conn, [tx("a", D1), tx("b", D2)])
    upsert_price(conn, price(D1, "152.3456"))
    before = conn.total_changes

    export_records(conn)

    assert conn.total_changes == before
