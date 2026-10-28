"""The summaries' text, locked by golden files (constitution: report output; research R9).

The golden files were not copied from the tool's output. They follow contracts/summaries.md:
the box-drawing layout comes from the rich prototype that produced the contract's example,
with exactly the settings the contract names, and every figure was checked by hand against
the arithmetic below. Any change to them must be stated in a spec.

Today is 2026-10-27 in America/New_York, and every price is final:
- 2026-05: 1.5 XMR at 150 (225) and 0.25 XMR at 160.004 (40.001), so $265.00.
- 2026-06: 1,234.5 XMR at 152.345 = 188,069.9025, so $188,069.90.
- 2026-09: 0.731 XMR at 158.5 = 115.8635 at 2026-10-01T03:30Z, which is 2026-09-30 23:30 in
  New York, so it is September and 2026-W40 there, though October in UTC.
- 2025-03: 0.5 XMR at 140 = 70, in no weekly or monthly row; only in 2025 and the annual total.
- Weekly and monthly totals: 225 + 40.001 + 188,069.9025 + 115.8635 = 188,450.767, so
  $188,450.77. Annual total: + 70 = $188,520.77.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from monero_income.orchestration import render_text
from monero_income.orchestration.summary import build_summaries
from monero_income.primitives.models import ExportRecord

GOLDEN = Path(__file__).parent.parent / "golden"
NY = ZoneInfo("America/New_York")
TODAY = date(2026, 10, 27)


def rec(txid: str, moment: str, amount: int, price: str) -> ExportRecord:
    occurred_at = int(datetime.fromisoformat(moment).replace(tzinfo=UTC).timestamp())
    return ExportRecord(txid, 1, amount, occurred_at, Decimal(price), "final")


UNMARKED = [
    rec("may-1", "2026-05-05T12:00:00", 1_500_000_000_000, "150"),
    rec("may-2", "2026-05-20T12:00:00", 250_000_000_000, "160.004"),
    rec("june", "2026-06-10T08:30:00", 1_234_500_000_000_000, "152.345"),
    rec("old", "2025-03-14T09:00:00", 500_000_000_000, "140"),
    rec("midnight", "2026-10-01T03:30:00", 731_000_000_000, "158.5"),
]


def stripped(text: str) -> list[str]:
    return [line.rstrip() for line in text.split("\n")]


@pytest.mark.parametrize(
    ("name", "records"),
    [("summaries_unmarked.txt", UNMARKED), ("summaries_empty.txt", [])],
)
def test_summaries_match_the_golden_file(name: str, records: list[ExportRecord]) -> None:
    text = render_text(build_summaries(records, TODAY, NY), None, styled=False)

    assert stripped(text) == stripped((GOLDEN / name).read_text())
