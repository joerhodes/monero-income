"""The export step: write every recorded transaction to the reports directory's CSV file.

Reading and writing are separate so run() can close the database between them.
"""

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from monero_income.orchestration.export_format import HEADER, Row, export_rows
from monero_income.primitives.export_db import export_records
from monero_income.primitives.export_file import write_export

EXPORT_FILE_NAME = "xmr_income.csv"


@dataclass(frozen=True)
class ExportSummary:
    path: Path  # absolute path of the export written
    transactions: int  # data rows written


def read_export_rows(conn: sqlite3.Connection) -> list[Row]:
    """Every recorded transaction as a formatted row, in export order."""
    return export_rows(export_records(conn))


def write_export_file(directory: Path, rows: Sequence[Row]) -> ExportSummary:
    """Replace ``directory/xmr_income.csv`` with ``rows`` under the header."""
    path = write_export(directory, EXPORT_FILE_NAME, HEADER, rows)
    return ExportSummary(path=path, transactions=len(rows))
