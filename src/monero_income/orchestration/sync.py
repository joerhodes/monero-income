"""Sync: fetch the wallet's incoming entries window by window and record the new ones."""

import sqlite3

from monero_income.orchestration.transform import (
    combine_by_txid,
    fetch_windows,
    first_window_start,
    select_new,
)
from monero_income.primitives.database import (
    insert_records,
    last_recorded_height,
    recorded_txids,
)
from monero_income.primitives.wallet_entries import parse_incoming
from monero_income.primitives.wallet_rpc import WalletRpc


def sync(conn: sqlite3.Connection, wallet: WalletRpc) -> int:
    """Record the wallet's new incoming transactions; return how many were inserted.

    Resumes just below the last recorded height. Each window is committed on its
    own, so an interrupted sync keeps every completed window.
    """
    start_after = first_window_start(last_recorded_height(conn))
    recorded = 0
    for lo, hi in fetch_windows(start_after, wallet.get_height()):
        try:
            records = combine_by_txid(parse_incoming(wallet.get_transfers(lo, hi).incoming))
            new = select_new(records, recorded_txids(conn, [r.txid for r in records]))
            if new:
                insert_records(conn, new)
                recorded += len(new)
        except BaseException:
            # Leave no open transaction and nothing from this window; earlier windows
            # are already committed.
            conn.rollback()
            raise
    return recorded
