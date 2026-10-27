"""SQLite read for the export: each transaction joined to its UTC day's price.

Only reads; never writes to the database (FR-024). Ordering is the caller's job.
"""

import sqlite3
from decimal import Decimal, InvalidOperation

from monero_income.primitives.errors import StorageReadError
from monero_income.primitives.models import ExportRecord


def export_records(conn: sqlite3.Connection) -> list[ExportRecord]:
    try:
        rows = conn.execute(
            """
            SELECT t.txid, t.height, t.amount_piconero, t.occurred_at, p.usd_price, p.status
            FROM transactions AS t
            LEFT JOIN daily_prices AS p ON p.date_utc = t.occurred_date
            """
        ).fetchall()
    except sqlite3.Error as error:
        raise StorageReadError(str(error)) from error
    return [
        ExportRecord(txid, height, amount, occurred_at, _price(text), status)
        for txid, height, amount, occurred_at, text, status in rows
    ]


def _price(text: str | None) -> Decimal | None:
    if text is None:
        return None
    try:
        price = Decimal(text)
    except InvalidOperation as error:
        raise StorageReadError(f"invalid stored price {text!r}") from error
    if not price.is_finite() or price <= 0:
        raise StorageReadError(f"invalid stored price {text!r}")
    return price
