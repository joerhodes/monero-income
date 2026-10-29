"""Pure aggregation of recorded transactions into weekly, monthly and annual income summaries.

No I/O.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import MAX_PREC, Decimal, Inexact, localcontext
from pathlib import Path
from zoneinfo import ZoneInfo

from monero_income.orchestration.valuation import usd_value
from monero_income.primitives.models import ExportRecord

WEEKLY_TITLE = "Weekly Summary"
MONTHLY_TITLE = "Monthly Summary"
ANNUAL_TITLE = "Annual Summary"
WEEKS = 26
MONTHS = 12
YEARS = 4
TOTAL_LABEL = "Total"


class SummaryDataError(Exception):
    """A record or summary breaks an invariant (FR-018)."""


@dataclass(frozen=True)
class PeriodFigures:
    label: str  # "2026-W44", "2026-10", "2026", or "Total"
    piconero: int  # exact XMR, all transactions
    usd: Decimal  # exact, unrounded; priced transactions only
    provisional: bool  # includes a provisional price
    unpriced: bool  # leaves out an unpriced transaction


@dataclass(frozen=True)
class Summary:
    title: str  # "Weekly Summary", "Monthly Summary", "Annual Summary"
    periods: tuple[PeriodFigures, ...]  # oldest first; 26, 12, or 4
    total: PeriodFigures  # label "Total"


@dataclass(frozen=True)
class IncomeSummaries:
    weekly: Summary
    monthly: Summary
    annual: Summary
    transactions: int  # all recorded transactions; 0 → the message


def summary_failure_message(reason: str, export_path: Path) -> str:
    """The FR-018 message. Here so run.py and summary_format.py can share it."""
    return (
        f"cannot show the income summaries: {reason}. The export was written to "
        f"{export_path}; recorded transactions and prices were kept."
    )


def local_date(occurred_at: int, zone: ZoneInfo | None) -> date:
    """The transaction's date in ``zone``, or in the machine's local zone when it is None."""
    return datetime.fromtimestamp(occurred_at, UTC).astimezone(zone).date()


def week_label(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def month_label(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def year_label(day: date) -> str:
    return f"{day.year}"


def week_labels(today: date) -> list[str]:
    """The ISO weeks ending with today's, oldest first."""
    monday = today - timedelta(days=today.weekday())
    return [week_label(monday - timedelta(weeks=back)) for back in range(WEEKS - 1, -1, -1)]


def month_labels(today: date) -> list[str]:
    """The calendar months ending with today's, oldest first."""
    first = today.year * 12 + today.month - 1
    return [f"{index // 12}-{index % 12 + 1:02d}" for index in range(first - MONTHS + 1, first + 1)]


def year_labels(today: date) -> list[str]:
    """The calendar years ending with today's, oldest first."""
    return [f"{year}" for year in range(today.year - YEARS + 1, today.year + 1)]


def exact_sum(values: Iterable[Decimal]) -> Decimal:
    """Add without rounding; raises rather than losing a digit (research R4)."""
    with localcontext() as context:
        context.prec = MAX_PREC
        context.traps[Inexact] = True
        total = Decimal(0)
        for value in values:
            total += value
        return total


def check_record(record: ExportRecord) -> None:
    """Raise SummaryDataError unless the record meets the invariants in research R10."""
    problem = _record_problem(record)
    if problem is not None:
        raise SummaryDataError(f"unexpected data for transaction {record.txid}: {problem}")


def _record_problem(record: ExportRecord) -> str | None:
    amount = record.amount_piconero
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        return "invalid amount"
    moment = record.occurred_at
    if not isinstance(moment, int) or isinstance(moment, bool):
        return "invalid moment"
    try:
        local_date(moment, None)
    except (OverflowError, OSError, ValueError):
        return "invalid moment"
    price = record.usd_price
    if price is not None and (
        not isinstance(price, Decimal) or not price.is_finite() or price <= 0
    ):
        return "invalid price"
    if (price is None) != (record.price_status is None) or record.price_status not in (
        None,
        "provisional",
        "final",
    ):
        return "invalid price status"
    return None


def summarize(
    dated: Sequence[tuple[date, ExportRecord]],
    labels: Sequence[str],
    label_of: Callable[[date], str],
    title: str,
) -> Summary:
    """One summary: a row per label, oldest first, and their total. Other records are skipped."""
    piconero = dict.fromkeys(labels, 0)
    usd: dict[str, list[Decimal]] = {label: [] for label in labels}
    provisional = dict.fromkeys(labels, False)
    unpriced = dict.fromkeys(labels, False)
    for day, record in dated:
        label = label_of(day)
        if label not in piconero:
            continue
        piconero[label] += record.amount_piconero
        if record.usd_price is None:
            unpriced[label] = True
        else:
            usd[label].append(usd_value(record.amount_piconero, record.usd_price))
            provisional[label] |= record.price_status == "provisional"
    periods = tuple(
        PeriodFigures(
            label, piconero[label], exact_sum(usd[label]), provisional[label], unpriced[label]
        )
        for label in labels
    )
    total = PeriodFigures(
        TOTAL_LABEL,
        sum(period.piconero for period in periods),
        exact_sum(period.usd for period in periods),
        any(period.provisional for period in periods),
        any(period.unpriced for period in periods),
    )
    return Summary(title, periods, total)


def build_summaries(
    records: Sequence[ExportRecord], today: date, zone: ZoneInfo | None
) -> IncomeSummaries:
    """The three summaries for ``today``, after checking every record (FR-018)."""
    for record in records:
        check_record(record)
    dated = [(local_date(record.occurred_at, zone), record) for record in records]
    return IncomeSummaries(
        weekly=summarize(dated, week_labels(today), week_label, WEEKLY_TITLE),
        monthly=summarize(dated, month_labels(today), month_label, MONTHLY_TITLE),
        annual=summarize(dated, year_labels(today), year_label, ANNUAL_TITLE),
        transactions=len(records),
    )
