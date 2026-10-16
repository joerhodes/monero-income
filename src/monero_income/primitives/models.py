"""Plain data passed between layers. Amounts are integer piconero, never float."""

from dataclasses import dataclass


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
