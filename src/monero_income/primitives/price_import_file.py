"""Price import CSV (contracts/import-csv.md): read the file, and parse it.

``read_import_file`` only reads. ``parse_import`` is pure and validates every row
before anything is written; the first problem rejects the whole file.
"""

import csv
import io
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from monero_income.primitives.errors import ImportFileError
from monero_income.primitives.models import ImportRow

HEADER = ("date_utc", "usd_price")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_PRICE = re.compile(r"[0-9]+(\.[0-9]+)?")


def read_import_file(path: Path) -> str:
    """The file's text. A leading BOM (from spreadsheet exports) is dropped."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise ImportFileError(None, "not valid UTF-8") from error
    except OSError as error:
        raise ImportFileError(None, error.strerror or type(error).__name__) from error


def parse_import(text: str) -> list[ImportRow]:
    """Validated rows, in file order; line numbers count the header as line 1."""
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if not rows or tuple(cell.strip() for cell in rows[0]) != HEADER:
        raise ImportFileError(None, f'header must be "{",".join(HEADER)}"')

    parsed: list[ImportRow] = []
    seen: dict[date, int] = {}
    for line, cells in enumerate(rows[1:], start=2):
        cells = [cell.strip() for cell in cells]
        if not any(cells):
            continue  # blank line
        if len(cells) > len(HEADER):
            raise ImportFileError(line, "expected 2 columns")
        day = _parse_date(cells[0], line)
        price = _parse_price(cells[1] if len(cells) > 1 else "", line)
        if day in seen:
            raise ImportFileError(line, f"date {day.isoformat()} already on line {seen[day]}")
        seen[day] = line
        parsed.append(ImportRow(line=line, date_utc=day, usd_price=price))
    return parsed


def _parse_date(text: str, line: int) -> date:
    if _DATE.fullmatch(text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
    raise ImportFileError(line, f'bad date "{text}"')


def _parse_price(text: str, line: int) -> Decimal:
    if not text:
        raise ImportFileError(line, "missing price")
    if not _PRICE.fullmatch(text):
        raise ImportFileError(line, f'bad price "{text}"')
    price = Decimal(text)
    if price <= 0:
        raise ImportFileError(line, "price must be greater than 0")
    return price
