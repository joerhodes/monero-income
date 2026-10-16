import itertools

from monero_income.orchestration.transform import (
    combine_by_txid,
    fetch_windows,
    first_window_start,
    select_new,
)
from monero_income.primitives.models import IncomingEntry, TransactionRecord

A = "a" * 64
B = "b" * 64
C = "c" * 64


def test_windows_cover_the_range_in_ascending_10000_block_steps() -> None:
    assert fetch_windows(0, 25000) == [(0, 10000), (10000, 20000), (20000, 25000)]


def test_no_windows_when_nothing_is_above_the_start() -> None:
    assert fetch_windows(0, 0) == []
    assert fetch_windows(500, 500) == []


def test_windows_start_after_the_given_height() -> None:
    assert fetch_windows(5, 10005) == [(5, 10005)]


def test_windows_are_ascending_gap_free_and_non_overlapping() -> None:
    windows = fetch_windows(939, 123_456)

    assert windows[0][0] == 939
    assert windows[-1][1] == 123_456
    for (_, previous_hi), (lo, hi) in itertools.pairwise(windows):
        assert lo == previous_hi
        assert lo < hi <= lo + 10_000


def test_combine_sums_amounts_per_txid_and_keeps_height_and_timestamp() -> None:
    entries = [
        IncomingEntry(txid=B, height=20, amount_piconero=400000000000, timestamp=2000),
        IncomingEntry(txid=A, height=10, amount_piconero=5, timestamp=1000),
        IncomingEntry(txid=B, height=20, amount_piconero=123456789012, timestamp=2000),
    ]

    assert combine_by_txid(entries) == [
        TransactionRecord(txid=A, height=10, amount_piconero=5, occurred_at=1000),
        TransactionRecord(txid=B, height=20, amount_piconero=523456789012, occurred_at=2000),
    ]


def test_combine_orders_by_ascending_height() -> None:
    entries = [
        IncomingEntry(txid=C, height=30, amount_piconero=1, timestamp=3),
        IncomingEntry(txid=A, height=10, amount_piconero=1, timestamp=1),
        IncomingEntry(txid=B, height=20, amount_piconero=1, timestamp=2),
    ]

    assert [record.height for record in combine_by_txid(entries)] == [10, 20, 30]
    assert combine_by_txid([]) == []


def test_first_window_start_overlaps_60_blocks_inclusive() -> None:
    # min_height is exclusive, so starting after last - 61 re-reads last - 60 .. last.
    assert first_window_start(None) == 0
    assert first_window_start(30) == 0
    assert first_window_start(1000) == 939


def test_select_new_drops_recorded_txids_and_keeps_order() -> None:
    records = [
        TransactionRecord(txid=A, height=10, amount_piconero=1, occurred_at=1),
        TransactionRecord(txid=B, height=20, amount_piconero=2, occurred_at=2),
        TransactionRecord(txid=C, height=30, amount_piconero=3, occurred_at=3),
    ]

    assert select_new(records, {B}) == [records[0], records[2]]
    assert select_new(records, set()) == records
    assert select_new(records, {A, B, C}) == []
