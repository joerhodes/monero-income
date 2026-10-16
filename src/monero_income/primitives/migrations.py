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
)

SCHEMA_VERSION = len(_STEPS)


def migrate(conn: sqlite3.Connection) -> None:
    """Apply any missing steps and the new user_version in one transaction.

    ``conn`` must use ``autocommit=False`` so the steps run inside a transaction.
    """
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    if current > SCHEMA_VERSION:
        raise SchemaTooNewError(current)
    if current == SCHEMA_VERSION:
        return
    try:
        for step in _STEPS[current:]:
            for statement in step:
                conn.execute(statement)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
