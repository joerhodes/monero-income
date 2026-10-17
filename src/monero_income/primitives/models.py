"""Plain data passed between layers.

Amounts are integer piconero and prices are Decimal; never float.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class IncomingEntry:
    """One entry from the wallet's ``in`` list: one (txid, subaddress) payment."""

    txid: str
    height: int
    amount_piconero: int
    timestamp: int


@dataclass(frozen=True)
class TransactionRecord:
    """One incoming transaction as stored: entries with the same txid combined."""

    txid: str
    height: int
    amount_piconero: int
    occurred_at: int  # UTC Unix seconds


@dataclass(frozen=True)
class DailyPrice:
    """The USD price of 1 XMR for one UTC calendar day."""

    date_utc: date
    usd_price: Decimal
    status: Literal["provisional", "final"]
    source: Literal["api", "import"]
    fetched_at: int  # UTC Unix seconds


@dataclass(frozen=True)
class PriceNeed:
    """A day with recorded transactions and no final price."""

    date_utc: date
    has_provisional: bool


@dataclass(frozen=True)
class ImportRow:
    """One validated row of a price import file; ``line`` is its line number in the file."""

    line: int
    date_utc: date
    usd_price: Decimal
