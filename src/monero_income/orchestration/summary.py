"""Pure aggregation of recorded transactions into weekly, monthly and annual income summaries.

No I/O.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

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
