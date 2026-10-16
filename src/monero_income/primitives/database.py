"""SQLite access: open (creating or migrating), read the sync position, insert records.

These functions only fetch or persist. Deciding which records to insert is done
by the caller (constitution IV).
"""

import sqlite3
from collections.abc import Sequence
from pathlib import Path

from monero_income.primitives.errors import StorageReadError, StorageWriteError
from monero_income.primitives.migrations import migrate
from monero_income.primitives.models import TransactionRecord

# Stay well under SQLite's limit on bound parameters per statement.
_TXID_LOOKUP_CHUNK = 500


def open_database(path: Path, timeout: float = 5.0) -> sqlite3.Connection:
    """Open the database at ``path``, creating it (and its directory) if missing.

    An existing file is never deleted, renamed, or recreated: if it can't be read
    as a database, ``StorageReadError`` is raised and the file is left alone.
    ``timeout`` is how long to wait for another connection's lock.
    """
    path = path.absolute()
    mode = "rw"
    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise StorageReadError(f"cannot create directory {path.parent}: {error}") from error
        mode = "rwc"
    try:
        conn = sqlite3.connect(
            f"{path.as_uri()}?mode={mode}", uri=True, autocommit=False, timeout=timeout
        )
    except sqlite3.Error as error:
        raise StorageReadError(str(error)) from error
    try:
        conn.execute("PRAGMA user_version").fetchone()
        migrate(conn)
    except sqlite3.DatabaseError as error:
        conn.close()
        raise StorageReadError(str(error)) from error
    except BaseException:
        conn.close()
        raise
    return conn


def last_recorded_height(conn: sqlite3.Connection) -> int | None:
    height: int | None = conn.execute("SELECT max(height) FROM transactions").fetchone()[0]
    return height


def recorded_txids(conn: sqlite3.Connection, txids: Sequence[str]) -> set[str]:
    """Return those of ``txids`` that are already recorded."""
    found: set[str] = set()
    for start in range(0, len(txids), _TXID_LOOKUP_CHUNK):
        chunk = txids[start : start + _TXID_LOOKUP_CHUNK]
        placeholders = ", ".join("?" * len(chunk))
        found.update(
            row[0]
            for row in conn.execute(
                f"SELECT txid FROM transactions WHERE txid IN ({placeholders})", chunk
            )
        )
    return found


def insert_records(conn: sqlite3.Connection, records: Sequence[TransactionRecord]) -> None:
    """Insert ``records`` and commit, as one transaction.

    Plain INSERT: an already-recorded txid is an error, never an update. On any
    failure the whole batch is rolled back.
    """
    if not records:
        return
    try:
        conn.executemany(
            "INSERT INTO transactions (txid, height, amount_piconero, occurred_at)"
            " VALUES (?, ?, ?, ?)",
            [(r.txid, r.height, r.amount_piconero, r.occurred_at) for r in records],
        )
        conn.commit()
    except (sqlite3.Error, OverflowError) as error:
        conn.rollback()
        raise StorageWriteError(str(error)) from error
    except BaseException:
        conn.rollback()
        raise
