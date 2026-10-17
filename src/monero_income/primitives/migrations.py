"""Schema migrations, keyed by ``PRAGMA user_version``.

Each step brings the schema from version N-1 to N. A database at version 0 is
empty and newly created. Steps are never edited once released; changes ship as
new steps.
"""

import sqlite3

from monero_income.primitives.errors import SchemaTooNewError

_STEPS: tuple[tuple[str, ...], ...] = (
    # 0 → 1: incoming transactions
    (
        """
        CREATE TABLE transactions (
            txid TEXT PRIMARY KEY CHECK (length(txid) = 64),
            height INTEGER NOT NULL CHECK (height > 0),
            amount_piconero INTEGER NOT NULL CHECK (amount_piconero > 0),
            occurred_at INTEGER NOT NULL,
            occurred_date TEXT GENERATED ALWAYS AS (date(occurred_at, 'unixepoch')) STORED
        )
        """,
        "CREATE INDEX transactions_height_idx ON transactions(height)",
    ),
    # 1 → 2: daily USD prices. Final prices are immutable and no price is ever deleted
    # (constitution VI); the triggers enforce that even against a direct UPDATE or DELETE.
    (
        """
        CREATE TABLE daily_prices (
            date_utc TEXT PRIMARY KEY
                CHECK (date_utc GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
            usd_price TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('provisional', 'final')),
            source TEXT NOT NULL CHECK (source IN ('api', 'import')),
            fetched_at INTEGER NOT NULL
        )
        """,
        """
        CREATE TRIGGER daily_prices_final_no_update
        BEFORE UPDATE ON daily_prices WHEN OLD.status = 'final'
        BEGIN
            SELECT RAISE(ABORT, 'final price is immutable');
        END
        """,
        """
        CREATE TRIGGER daily_prices_no_delete
        BEFORE DELETE ON daily_prices
        BEGIN
            SELECT RAISE(ABORT, 'prices are never deleted');
        END
        """,
    ),
)

SCHEMA_VERSION = len(_STEPS)


def migrate(conn: sqlite3.Connection, to_version: int = SCHEMA_VERSION) -> None:
    """Apply any missing steps and the new user_version in one transaction.

    ``conn`` must use ``autocommit=False`` so the steps run inside a transaction.
    ``to_version`` lets tests build a database at an earlier released schema.
    """
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    if current > SCHEMA_VERSION:
        raise SchemaTooNewError(current)
    if current >= to_version:
        return
    try:
        for step in _STEPS[current:to_version]:
            for statement in step:
                conn.execute(statement)
        conn.execute(f"PRAGMA user_version = {to_version}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
