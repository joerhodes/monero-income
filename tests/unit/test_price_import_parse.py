from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration.price_import import select_imports
from monero_income.primitives.errors import ImportFileError
from monero_income.primitives.models import ImportRow
from monero_income.primitives.price_import_file import parse_import, read_import_file

HEADER = "date_utc,usd_price\n"


def test_valid_file_is_parsed_exactly() -> None:
    text = HEADER + "2024-03-01,151.234\n\n 2024-03-02 , 149.9 \n2024-03-03,150\n"

    assert parse_import(text) == [
        ImportRow(line=2, date_utc=date(2024, 3, 1), usd_price=Decimal("151.234")),
        ImportRow(line=4, date_utc=date(2024, 3, 2), usd_price=Decimal("149.9")),
        ImportRow(line=5, date_utc=date(2024, 3, 3), usd_price=Decimal("150")),
    ]


def test_header_whitespace_is_trimmed_and_header_only_is_empty() -> None:
    assert parse_import(" date_utc , usd_price \n") == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", 'header must be "date_utc,usd_price"'),
        ("date,price\n2024-03-01,1\n", 'header must be "date_utc,usd_price"'),
        ("usd_price,date_utc\n", 'header must be "date_utc,usd_price"'),
        (HEADER + "2024-03-01,1,extra\n", "line 2: expected 2 columns"),
        (HEADER + "2024-03-01,1\n2024-13-01,1\n", 'line 3: bad date "2024-13-01"'),
        (HEADER + "2024-1-1,1\n", 'line 2: bad date "2024-1-1"'),
        (HEADER + "20240301,1\n", 'line 2: bad date "20240301"'),
        (HEADER + "2024-03-01,\n", "line 2: missing price"),
        (HEADER + "2024-03-01\n", "line 2: missing price"),
        (HEADER + "2024-03-01,0\n", "line 2: price must be greater than 0"),
        (HEADER + "2024-03-01,0.000\n", "line 2: price must be greater than 0"),
        (HEADER + "2024-03-01,-1\n", 'line 2: bad price "-1"'),
        (HEADER + "2024-03-01,1e2\n", 'line 2: bad price "1e2"'),
        (HEADER + "2024-03-01,NaN\n", 'line 2: bad price "NaN"'),
        (HEADER + '2024-03-01,"1,000.5"\n', 'line 2: bad price "1,000.5"'),
        (
            HEADER + "2024-02-28,1\n2024-02-29,1\n2024-03-01,1\n2024-03-01,2\n",
            "line 5: date 2024-03-01 already on line 4",
        ),
    ],
)
def test_first_problem_rejects_the_whole_file(text: str, message: str) -> None:
    with pytest.raises(ImportFileError) as excinfo:
        parse_import(text)

    assert str(excinfo.value) == message


def test_select_imports_keeps_old_unpriced_rows_and_counts_the_rest() -> None:
    cutoff = date(2025, 10, 18)
    rows = [
        ImportRow(2, date(2025, 3, 1), Decimal("1")),  # old, unpriced: kept
        ImportRow(3, date(2025, 3, 2), Decimal("2")),  # old, already priced: skipped
        ImportRow(4, date(2025, 10, 17), Decimal("3")),  # old (day before cutoff): kept
        ImportRow(5, date(2025, 10, 18), Decimal("4")),  # inside the window: skipped
        ImportRow(6, date(2026, 10, 1), Decimal("5")),  # recent: skipped
    ]

    kept, skipped = select_imports(rows, {date(2025, 3, 2)}, cutoff)

    assert [row.line for row in kept] == [2, 4]
    assert skipped == 3


def test_read_import_file_drops_a_leading_bom(tmp_path: Path) -> None:
    path = tmp_path / "prices.csv"
    path.write_bytes(b"\xef\xbb\xbfdate_utc,usd_price\n2024-03-01,151.234\n")

    assert parse_import(read_import_file(path)) == [
        ImportRow(line=2, date_utc=date(2024, 3, 1), usd_price=Decimal("151.234"))
    ]


def test_read_import_file_rejects_non_utf8(tmp_path: Path) -> None:
    path = tmp_path / "prices.csv"
    path.write_bytes(b"date_utc,usd_price\n2024-03-01,\xff\n")

    with pytest.raises(ImportFileError, match="not valid UTF-8"):
        read_import_file(path)
