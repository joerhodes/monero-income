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
    PeriodFigures,
    SummaryDataError,
    build_summaries,
)
from monero_income.orchestration.summary_format import (
    LEGEND,
    NO_TRANSACTIONS,
    format_usd,
    format_xmr_grouped,
    marks,
    render_text,
    summary_renderable,
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


# Marks and legend (FR-012, US2)

PROVISIONAL_LINE = "* includes a provisional price, which may still change"
UNPRICED_LINE = "? leaves out transactions that have no price yet"


def marked() -> IncomeSummaries:
    """The contract's example records: 2026-W43 is unpriced, 2026-W44 provisional."""
    records = [
        ExportRecord("a", 1, 1_500_000_000_000, ts("2025-03-14T09:00:00"), Decimal(150), "final"),
        ExportRecord(
            "b", 2, 250_000_000_000, ts("2026-05-05T12:00:00"), Decimal("160.004"), "final"
        ),
        ExportRecord(
            "c", 3, 1_234_500_000_000_000, ts("2026-06-10T08:30:00"), Decimal("152.345"), "final"
        ),
        ExportRecord("d", 4, 731_000_000_000, ts("2026-10-20T18:45:10"), None, None),
        ExportRecord(
            "e",
            5,
            2_000_000_000_000,
            ts("2026-10-27T11:00:00"),
            Decimal("163.40000000000001"),
            "provisional",
        ),
    ]
    return build_summaries(records, TODAY, NY)


def only(provisional: bool = False, unpriced: bool = False) -> IncomeSummaries:
    """``summaries()`` with the first weekly row flagged as given."""
    plain = summaries()
    first = dataclasses.replace(plain.weekly.periods[0], provisional=provisional, unpriced=unpriced)
    weekly = dataclasses.replace(plain.weekly, periods=(first, *plain.weekly.periods[1:]))
    return dataclasses.replace(plain, weekly=weekly)


@pytest.mark.parametrize(
    ("provisional", "unpriced", "text"),
    [(False, False, ""), (True, False, "*"), (False, True, "?"), (True, True, "*?")],
)
def test_marks(provisional: bool, unpriced: bool, text: str) -> None:
    figures = PeriodFigures("2026-W44", 0, Decimal(0), provisional, unpriced)
    assert marks(figures) == text


def test_marked_usd_cells_are_padded_to_the_longest_mark() -> None:
    for summary in (marked().weekly, marked().monthly, marked().annual):
        table = summary_table(summary)
        assert len(table.columns) == 3
        rows = (*summary.periods, summary.total)
        longest = max(len(marks(figures)) for figures in rows)
        assert longest > 0
        cells = [str(cell) for cell in table.columns[2].cells]
        assert cells == [format_usd(f.usd) + " " + marks(f).ljust(longest) for f in rows]


def test_marked_rows_stay_right_aligned() -> None:
    text = lines(render_text(marked(), None, False))
    assert "│ 2026-W43 │     0.731000000000 │        $0.00 ? │" in text
    assert "│ 2026-W44 │     2.000000000000 │      $326.80 * │" in text
    assert "│ 2026-W19 │     0.250000000000 │         $40.00 │" in text
    assert "│ Total    │ 1,237.481000000000 │ $188,436.70 *? │" in text


def test_a_table_without_marks_has_no_suffix() -> None:
    table = summary_table(summaries().weekly)
    assert [str(cell) for cell in table.columns[2].cells] == [
        format_usd(f.usd) for f in (*summaries().weekly.periods, summaries().weekly.total)
    ]


def test_legend_texts() -> None:
    assert LEGEND == {"*": PROVISIONAL_LINE, "?": UNPRICED_LINE}


@pytest.mark.parametrize(
    ("flagged", "legend"),
    [
        pytest.param(marked, [PROVISIONAL_LINE, UNPRICED_LINE], id="both"),
        pytest.param(lambda: only(provisional=True), [PROVISIONAL_LINE], id="provisional"),
        pytest.param(lambda: only(unpriced=True), [UNPRICED_LINE], id="unpriced"),
    ],
)
def test_the_legend_follows_the_layout_with_only_the_marks_shown(
    flagged: Callable[[], IncomeSummaries], legend: list[str]
) -> None:
    text = lines(render_text(flagged(), None, False))
    count = len(legend)
    assert text[-1] == ""
    assert text[-1 - count : -1] == legend
    assert text[-2 - count] == ""
    assert text[-3 - count].startswith("╰")


def test_no_marks_means_no_legend() -> None:
    text = render_text(summaries(), None, False)
    assert PROVISIONAL_LINE not in text
    assert UNPRICED_LINE not in text


def test_the_legend_is_never_wrapped() -> None:
    _, needed = summary_renderable(marked(), None)
    assert needed >= len(PROVISIONAL_LINE) == 54
    text = lines(render_text(marked(), None, False))
    assert PROVISIONAL_LINE in text
    assert UNPRICED_LINE in text


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
