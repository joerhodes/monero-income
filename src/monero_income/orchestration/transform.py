"""Pure steps of a sync: which height windows to fetch, and how entries become records."""

from collections.abc import Sequence, Set

from monero_income.primitives.models import IncomingEntry, TransactionRecord

WINDOW_SIZE = 10_000  # blocks, about 14 days (research R2)
OVERLAP_BLOCKS = 60  # re-read below the last recorded height, to catch reorgs


def first_window_start(last_height: int | None) -> int:
    """Where a sync starts: just below ``last_height - OVERLAP_BLOCKS``, or 0 on a first run.

    The wallet's ``min_height`` is exclusive, so starting after ``last - 61`` re-reads
    ``last - 60`` through ``last`` inclusive (research R5).
    """
    if last_height is None:
        return 0
    return max(last_height - OVERLAP_BLOCKS - 1, 0)


def fetch_windows(start_after: int, wallet_height: int) -> list[tuple[int, int]]:
    """Ascending, consecutive ``(lo, hi]`` windows covering ``start_after < h <= wallet_height``."""
    windows: list[tuple[int, int]] = []
    lo = start_after
    while lo < wallet_height:
        hi = min(lo + WINDOW_SIZE, wallet_height)
        windows.append((lo, hi))
        lo = hi
    return windows


def combine_by_txid(entries: Sequence[IncomingEntry]) -> list[TransactionRecord]:
    """One record per txid, amounts summed, in ascending height order.

    A transaction paying several subaddresses arrives as several entries with the
    same txid, height and timestamp.
    """
    combined: dict[str, TransactionRecord] = {}
    for entry in entries:
        existing = combined.get(entry.txid)
        if existing is None:
            combined[entry.txid] = TransactionRecord(
                txid=entry.txid,
                height=entry.height,
                amount_piconero=entry.amount_piconero,
                occurred_at=entry.timestamp,
            )
        else:
            combined[entry.txid] = TransactionRecord(
                txid=existing.txid,
                height=existing.height,
                amount_piconero=existing.amount_piconero + entry.amount_piconero,
                occurred_at=existing.occurred_at,
            )
    return sorted(combined.values(), key=lambda record: (record.height, record.txid))


def select_new(
    records: Sequence[TransactionRecord], recorded_txids: Set[str]
) -> list[TransactionRecord]:
    """Drop records whose txid is already recorded, keeping order."""
    return [record for record in records if record.txid not in recorded_txids]
