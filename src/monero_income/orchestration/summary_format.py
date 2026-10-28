"""The text printed after the export line by every successful run.

This is report output under the constitution: any change to it must be stated in a spec and
update the golden files (``tests/golden/summaries_*.txt``) in the same change.

The tables are built with rich and rendered only into an in-memory Console (research R7).
"""

import io
from decimal import Decimal
from pathlib import Path

from rich import box
from rich.console import Console, Group, RenderableType
from rich.measure import Measurement
from rich.table import Table
from rich.text import Text

from monero_income.orchestration.export_format import round_cents
from monero_income.orchestration.run import RunResult, SummaryError
from monero_income.orchestration.summary import (
    MONTHS,
    WEEKS,
    YEARS,
    IncomeSummaries,
    Summary,
    SummaryDataError,
    summary_failure_message,
)

NO_TRANSACTIONS = "No transactions to summarize yet."
TABLE_GAP = 4  # columns between the side-by-side tables
PROBE_WIDTH = 10_000  # wide enough that measuring never shrinks a table


def format_xmr_grouped(piconero: int) -> str:
    whole, fraction = divmod(piconero, 10**12)
    return f"{whole:,}.{fraction:012d}"


def format_usd(value: Decimal) -> str:
    return "$" + format(round_cents(value), ",f")


def check_summaries(summaries: IncomeSummaries) -> None:
    """Raise SummaryDataError unless the summaries can be shown as they are (research R10)."""
    for summary, count in (
        (summaries.weekly, WEEKS),
        (summaries.monthly, MONTHS),
        (summaries.annual, YEARS),
    ):
        if len(summary.periods) != count:
            raise SummaryDataError(
                f"unexpected data in {summary.title}: {len(summary.periods)} periods, not {count}"
            )
        for figures in (*summary.periods, summary.total):
            piconero, usd = figures.piconero, figures.usd
            if not isinstance(piconero, int) or isinstance(piconero, bool) or piconero < 0:
                raise SummaryDataError(
                    f"unexpected data in {summary.title} {figures.label}: invalid XMR"
                )
            if not isinstance(usd, Decimal) or not usd.is_finite() or usd < 0:
                raise SummaryDataError(
                    f"unexpected data in {summary.title} {figures.label}: invalid USD"
                )


def summary_table(summary: Summary) -> Table:
    table = Table(title=summary.title, box=box.ROUNDED, header_style="bold")
    table.add_column("Period", justify="left", no_wrap=True)
    table.add_column("XMR", justify="right", no_wrap=True)
    table.add_column("USD", justify="right", no_wrap=True)
    for figures in summary.periods:
        table.add_row(*_cells(figures.label, figures.piconero, figures.usd))
    table.add_section()
    table.add_row(*_cells(summary.total.label, summary.total.piconero, summary.total.usd))
    return table


def _cells(label: str, piconero: int, usd: Decimal) -> tuple[Text, Text, Text]:
    # Text cells are never parsed as markup or highlighted.
    return Text(label), Text(format_xmr_grouped(piconero)), Text(format_usd(usd))


def table_width(table: Table) -> int:
    probe = Console(width=PROBE_WIDTH, file=io.StringIO())
    return Measurement.get(probe, probe.options, table).maximum


def summary_renderable(summaries: IncomeSummaries, width: int | None) -> tuple[RenderableType, int]:
    """The layout to print and the console width it needs."""
    if summaries.transactions == 0:
        return Text(NO_TRANSACTIONS), len(NO_TRANSACTIONS)
    weekly, monthly, annual = (
        summary_table(summary)
        for summary in (summaries.weekly, summaries.monthly, summaries.annual)
    )
    needed = max(table_width(table) for table in (weekly, monthly, annual))
    return Group(weekly, Text(""), monthly, Text(""), annual), needed


def render_text(summaries: IncomeSummaries, width: int | None, styled: bool) -> str:
    """The summaries' text. ``width`` is the terminal's (None when not a terminal).

    The console is never narrower than the layout, so rich never shrinks or truncates a
    figure; ``styled`` adds the bold header and the title style (terminal only).
    """
    check_summaries(summaries)
    renderable, needed = summary_renderable(summaries, width)
    buffer = io.StringIO()
    console = Console(
        file=buffer,
        width=max(width or 0, needed),
        color_system="standard" if styled else None,
        force_terminal=styled,
        highlight=False,
        markup=False,
        emoji=False,
        legacy_windows=False,
    )
    console.print(renderable)
    return buffer.getvalue()


def summary_text(result: RunResult, export_path: Path, width: int | None, styled: bool) -> str:
    """The guarded rendering stage (FR-018): the complete text, or SummaryError.

    ``export_path`` is the export the run wrote; the error message names it.
    """
    if result.summaries is None:
        return ""
    try:
        return render_text(result.summaries, width, styled)
    except SummaryDataError as error:
        reason = str(error)
    except Exception as error:  # deliberate: any rendering failure is one clean error
        reason = f"unexpected {type(error).__name__}: {error}"
    raise SummaryError(summary_failure_message(reason, export_path), result)
