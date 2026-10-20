"""Answers from the price source, and parsing of a `/history` body. Pure: no I/O.

The body must have been decoded with ``parse_float=Decimal``, so prices arrive
exact. A ``float`` here means it wasn't, and is rejected rather than trusted.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Price:
    usd_price: Decimal


@dataclass(frozen=True)
class NoPrice:
    """No usable price for the day: not published yet, missing, or invalid."""

    reason: str


@dataclass(frozen=True)
class OutsideHistory:
    """The day is older than the source's history period (HTTP 401, error_code 10012)."""


PriceAnswer = Price | NoPrice | OutsideHistory


def parse_history_price(body: object) -> Price | NoPrice:
    """Read ``market_data.current_price.usd`` from a decoded `/history` body."""
    usd = _get(_get(_get(body, "market_data"), "current_price"), "usd")
    if usd is None:
        return NoPrice("no price for this date")
    if isinstance(usd, bool):
        return NoPrice("invalid price")
    if isinstance(usd, int):
        usd = Decimal(usd)
    if not isinstance(usd, Decimal) or not usd.is_finite() or usd <= 0:
        return NoPrice("invalid price")
    return Price(usd)


def _get(value: object, key: str) -> object:
    return value.get(key) if isinstance(value, dict) else None
