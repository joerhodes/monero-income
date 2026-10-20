"""SQLite access for daily USD prices. Only fetches or persists (constitution IV).

Prices are stored as plain decimal text, so they round-trip exactly. A final price
is never changed: the upsert only replaces provisional rows, and schema triggers
reject any other update or delete.
"""

import sqlite3
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from monero_income.primitives.errors import StorageWriteError
from monero_income.primitives.models import DailyPrice, PriceNeed

# Stay well under SQLite's limit on bound parameters per statement.
_DAY_LOOKUP_CHUNK = 500


def price_needs(conn: sqlite3.Connection) -> list[PriceNeed]:
    """Days with recorded transactions and no final price, oldest first."""
    rows = conn.execute(
        """
        SELECT DISTINCT t.occurred_date, p.status
        FROM transactions AS t
        LEFT JOIN daily_prices AS p ON p.date_utc = t.occurred_date
        WHERE p.status IS NULL OR p.status = 'provisional'
        ORDER BY t.occurred_date
        """
    ).fetchall()
    return [
        PriceNeed(date_utc=date.fromisoformat(day), has_provisional=status == "provisional")
        for day, status in rows
    ]


def upsert_price(conn: sqlite3.Connection, price: DailyPrice) -> None:
    """Record a looked-up price and commit. A final price already recorded is left as is."""
    try:
        conn.execute(
            """
            INSERT INTO daily_prices (date_utc, usd_price, status, source, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date_utc) DO UPDATE SET
                usd_price = excluded.usd_price,
                status = excluded.status,
                source = excluded.source,
                fetched_at = excluded.fetched_at
            WHERE daily_prices.status = 'provisional'
            """,
            _row(price),
        )
        conn.commit()
    except sqlite3.Error as error:
        conn.rollback()
        raise StorageWriteError(str(error)) from error
    except BaseException:
        conn.rollback()
        raise


def priced_days(conn: sqlite3.Connection, days: Sequence[date]) -> set[date]:
    """Return those of ``days`` that have a recorded price (provisional or final)."""
    found: set[date] = set()
    texts = [day.isoformat() for day in days]
    for start in range(0, len(texts), _DAY_LOOKUP_CHUNK):
        chunk = texts[start : start + _DAY_LOOKUP_CHUNK]
        placeholders = ", ".join("?" * len(chunk))
        found.update(
            date.fromisoformat(row[0])
            for row in conn.execute(
                f"SELECT date_utc FROM daily_prices WHERE date_utc IN ({placeholders})", chunk
            )
        )
    return found


def insert_imported(conn: sqlite3.Connection, prices: Sequence[DailyPrice]) -> None:
    """Insert imported prices in one transaction. Any conflict rolls back all of them."""
    if not prices:
        return
    try:
        conn.executemany(
            "INSERT INTO daily_prices (date_utc, usd_price, status, source, fetched_at)"
            " VALUES (?, ?, ?, ?, ?)",
            [_row(price) for price in prices],
        )
        conn.commit()
    except sqlite3.Error as error:
        conn.rollback()
        raise StorageWriteError(str(error)) from error
    except BaseException:
        conn.rollback()
        raise


def all_days_final(conn: sqlite3.Connection) -> bool:
    """True when at least one transaction is recorded and every transaction day is final."""
    has_transactions, has_unfinished = conn.execute(
        """
        SELECT
            EXISTS (SELECT 1 FROM transactions),
            EXISTS (
                SELECT 1 FROM transactions AS t
                LEFT JOIN daily_prices AS p ON p.date_utc = t.occurred_date
                WHERE p.status IS NULL OR p.status = 'provisional'
            )
        """
    ).fetchone()
    return bool(has_transactions) and not has_unfinished


def _row(price: DailyPrice) -> tuple[str, str, str, str, int]:
    return (
        price.date_utc.isoformat(),
        _decimal_text(price.usd_price),
        price.status,
        price.source,
        price.fetched_at,
    )


def _decimal_text(value: Decimal) -> str:
    """Plain decimal text with no exponent; Decimal(text) == value exactly."""
    return format(value, "f")
