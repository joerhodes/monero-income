"""The summaries' text, rendered with rich (contracts/summaries.md, research R5, R7)."""

import dataclasses
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from rich import box
from rich.table import Table

from monero_income.orchestration.summary import (
    IncomeSummaries,
    SummaryDataError,
    build_summaries,
)
from monero_income.orchestration.summary_format import (
    NO_TRANSACTIONS,
    format_usd,
    format_xmr_grouped,
    render_text,
    summary_table,
)
from monero_income.primitives.models import ExportRecord

NY = ZoneInfo("America/New_York")
TODAY = date(2026, 10, 27)


def ts(moment: str) -> int:
    return int(datetime.fromisoformat(moment).replace(tzinfo=UTC).timestamp())


def summaries() -> IncomeSummaries:
    records = [
        ExportRecord("a", 1, 1_500_000_000_000, ts("2026-05-05T12:00:00"), Decimal(150), "final"),
        ExportRecord(
            "b", 2, 1_234_500_000_000_000, ts("2026-06-10T08:30:00"), Decimal("152.345"), "final"
        ),
    ]
    return build_summaries(records, TODAY, NY)


def lines(text: str) -> list[str]:
    return [line.rstrip() for line in text.split("\n")]


# Number formats


@pytest.mark.parametrize(
    ("piconero", "text"),
    [
        (0, "0.000000000000"),
        (1, "0.000000000001"),
        (1_750_000_000_000, "1.750000000000"),
        (1_234_500_000_000_000, "1,234.500000000000"),
        (10**21, "1,000,000,000.000000000000"),
    ],
)
def test_format_xmr_grouped(piconero: int, text: str) -> None:
    assert format_xmr_grouped(piconero) == text


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (Decimal(0), "$0.00"),
        (Decimal("265.001"), "$265.00"),
        (Decimal("1234567.895"), "$1,234,567.90"),
        (Decimal("0.125"), "$0.13"),
        (Decimal("0.00000000015"), "$0.00"),
    ],
)
def test_format_usd(value: Decimal, text: str) -> None:
    assert format_usd(value) == text


# One table


def test_summary_table_style_and_columns() -> None:
    weekly = summaries().weekly
    table = summary_table(weekly)
    assert isinstance(table, Table)
    assert table.box is box.ROUNDED
    assert table.header_style == "bold"
    assert table.title == weekly.title
    assert [str(c.header) for c in table.columns] == ["Period", "XMR", "USD"]
    assert [c.justify for c in table.columns] == ["left", "right", "right"]
    assert all(c.no_wrap for c in table.columns)
    assert table.row_count == 27
    assert table.rows[-2].end_section
    assert not any(r.end_section for r in table.rows[:-2])


def test_rendered_table_shape() -> None:
    text = lines(render_text(summaries(), None, styled=False))
    assert text[0].strip() == "Weekly Summary"
    assert text[1].startswith("╭")
    assert text[2].startswith("│ Period   │")
    assert text[2].endswith("USD │")
    assert text[3].startswith("├")
    assert text[4].startswith("│ 2026-W19 │")
    assert text[29].startswith("│ 2026-W44 │")
    assert text[30].startswith("├")
    assert text[31].startswith("│ Total    │")
    assert text[32].startswith("╰")
    june = next(line for line in text if line.startswith("│ 2026-W24 │"))
    assert june == "│ 2026-W24 │ 1,234.500000000000 │ $188,069.90 │"
    may = next(line for line in text if line.startswith("│ 2026-W19 │"))
    assert may == "│ 2026-W19 │     1.500000000000 │     $225.00 │"


def test_plain_text_has_no_ansi_codes_and_styled_text_has_a_bold_header() -> None:
    assert "\x1b" not in render_text(summaries(), None, styled=False)
    styled = lines(render_text(summaries(), None, styled=True))
    header = next(line for line in styled if "Period" in line)
    assert "\x1b[1m" in header


def test_styled_text_has_no_highlighting_and_no_markup() -> None:
    plain = summaries()
    weekly = dataclasses.replace(
        plain.weekly,
        periods=(
            dataclasses.replace(plain.weekly.periods[0], label="[bold]x"),
            *plain.weekly.periods[1:],
        ),
    )
    text = render_text(dataclasses.replace(plain, weekly=weekly), None, styled=True)
    rows = [line for line in lines(text) if line.startswith("│ 20") or line.startswith("│ Total")]
    assert rows
    assert all("\x1b" not in line for line in rows)
    assert "│ [bold]x  │" in text


def test_tables_follow_one_another_without_a_legend() -> None:
    text = lines(render_text(summaries(), None, False))
    assert text[33] == ""
    assert text[34].strip() == "Monthly Summary"
    assert text[52].startswith("╰")
    assert text[53] == ""
    assert text[54].strip() == "Annual Summary"
    assert text[-2].startswith("╰")
    assert text[-1] == ""


def test_a_narrow_width_never_truncates() -> None:
    text = render_text(summaries(), 30, False)
    assert "1,234.500000000000" in text
    assert "$188,069.90" in text
    assert "…" not in text


def test_no_transactions_is_one_line() -> None:
    empty = build_summaries([], TODAY, NY)
    assert render_text(empty, None, False) == NO_TRANSACTIONS + "\n"
    assert NO_TRANSACTIONS == "No transactions to summarize yet."


# Input checks (research R10)


def broken_weekly(**changes: object) -> IncomeSummaries:
    plain = summaries()
    first = dataclasses.replace(plain.weekly.periods[0], **changes)  # type: ignore[arg-type]
    weekly = dataclasses.replace(plain.weekly, periods=(first, *plain.weekly.periods[1:]))
    return dataclasses.replace(plain, weekly=weekly)


@pytest.mark.parametrize(
    "broken",
    [
        pytest.param(
            lambda: dataclasses.replace(
                summaries(),
                weekly=dataclasses.replace(
                    summaries().weekly, periods=summaries().weekly.periods[:25]
                ),
            ),
            id="25 weekly periods",
        ),
        pytest.param(lambda: broken_weekly(piconero=-1), id="negative XMR"),
        pytest.param(lambda: broken_weekly(usd=Decimal("NaN")), id="NaN USD"),
        pytest.param(lambda: broken_weekly(usd=Decimal(-1)), id="negative USD"),
    ],
)
def test_render_text_rejects_malformed_summaries(broken: Callable[[], IncomeSummaries]) -> None:
    with pytest.raises(SummaryDataError, match="Weekly Summary"):
        render_text(broken(), None, False)
