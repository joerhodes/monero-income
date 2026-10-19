"""The optional price import step (US4): fill old unpriced days from a CSV file."""

import sqlite3
from collections.abc import Callable, Sequence, Set
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from monero_income.orchestration.valuation import history_cutoff
from monero_income.primitives.models import DailyPrice, ImportRow
from monero_income.primitives.price_import_file import parse_import, read_import_file
from monero_income.primitives.prices_db import insert_imported, priced_days


@dataclass(frozen=True)
class ImportSummary:
    imported: int
    skipped: int


def select_imports(
    rows: Sequence[ImportRow], already_priced: Set[date], cutoff: date
) -> tuple[list[ImportRow], int]:
    """Rows to import (older than ``cutoff`` and unpriced), and how many were skipped. Pure."""
    kept = [row for row in rows if row.date_utc < cutoff and row.date_utc not in already_priced]
    return kept, len(rows) - len(kept)


def import_prices(
    conn: sqlite3.Connection, path: Path, *, today: date, clock: Callable[[], datetime]
) -> ImportSummary:
    """Validate the whole file, then insert the selected rows as final prices in one
    transaction. Days inside the history period are left to the price source, and a
    recorded price is never replaced (FR-019, FR-020)."""
    rows = parse_import(read_import_file(path))
    already_priced = priced_days(conn, [row.date_utc for row in rows])
    kept, skipped = select_imports(rows, already_priced, history_cutoff(today))
    fetched_at = int(clock().timestamp())
    insert_imported(
        conn,
        [
            DailyPrice(
                date_utc=row.date_utc,
                usd_price=row.usd_price,
                status="final",
                source="import",
                fetched_at=fetched_at,
            )
            for row in kept
        ],
    )
    return ImportSummary(imported=len(kept), skipped=skipped)
