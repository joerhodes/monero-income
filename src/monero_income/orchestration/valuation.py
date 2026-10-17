"""Pure valuation rules: history cutoff, lookup order, settling, pacing defaults, USD value."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, Inexact, localcontext
from typing import Literal

from monero_income.primitives.models import PriceNeed

HISTORY_DAYS = 364  # one day of margin inside the source's 365-day limit (research R2)
SETTLING_PERIOD = timedelta(hours=1)  # after the UTC day ends (spec FR-021)
DELAY_WITH_KEY = Decimal("2.5")  # seconds; conservative for the Demo tier (research R1)
DELAY_WITHOUT_KEY = Decimal("6.0")  # seconds; the keyless floor of 10 calls/min
PICONERO_EXPONENT = -12


@dataclass(frozen=True)
class LookupPlan:
    requestable: list[PriceNeed]  # oldest first (FR-024)
    too_old: list[PriceNeed]  # older than the history period (FR-011)


def history_cutoff(today: date) -> date:
    """The oldest day that may be requested."""
    return today - timedelta(days=HISTORY_DAYS)


def plan_lookups(needs: Sequence[PriceNeed], today: date) -> LookupPlan:
    cutoff = history_cutoff(today)
    ordered = sorted(needs, key=lambda need: need.date_utc)
    return LookupPlan(
        requestable=[need for need in ordered if need.date_utc >= cutoff],
        too_old=[need for need in ordered if need.date_utc < cutoff],
    )


def settled_at(day: date) -> datetime:
    """When a day's price can be final: one hour after the UTC day ends."""
    return datetime.combine(day + timedelta(days=1), time(), tzinfo=UTC) + SETTLING_PERIOD


def price_status(day: date, now: datetime) -> Literal["provisional", "final"]:
    """Status for a price looked up at ``now``. Decided at lookup time only (FR-022)."""
    return "final" if now >= settled_at(day) else "provisional"


def default_delay(has_key: bool) -> Decimal:
    return DELAY_WITH_KEY if has_key else DELAY_WITHOUT_KEY


def usd_value(amount_piconero: int, usd_price: Decimal) -> Decimal:
    """Exact USD value of an amount at a price; raises rather than rounding (research R4)."""
    amount = Decimal(amount_piconero)
    digits = len(amount.as_tuple().digits) + len(usd_price.as_tuple().digits) + 2
    with localcontext() as context:
        context.prec = digits
        context.traps[Inexact] = True
        return (amount * usd_price).scaleb(PICONERO_EXPONENT)
