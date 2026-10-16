"""Sync: fetch the wallet's incoming entries window by window and record them."""

import sqlite3

from monero_income.orchestration.transform import combine_by_txid, fetch_windows
from monero_income.primitives.database import insert_records
from monero_income.primitives.wallet_entries import parse_incoming
from monero_income.primitives.wallet_rpc import WalletRpc


def sync(conn: sqlite3.Connection, wallet: WalletRpc) -> int:
    """Record the wallet's incoming transactions; return how many were inserted.

    Each window is committed on its own, so an interrupted sync keeps every
    completed window.
    """
    start_after = 0
    recorded = 0
    for lo, hi in fetch_windows(start_after, wallet.get_height()):
        records = combine_by_txid(parse_incoming(wallet.get_transfers(lo, hi).incoming))
        insert_records(conn, records)
        recorded += len(records)
    return recorded
