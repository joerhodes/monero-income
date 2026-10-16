"""US3: an interrupted sync keeps completed windows; the next run finishes the job."""

from pathlib import Path

import pytest

from monero_income.orchestration import RunError
from monero_income.primitives.database import open_database
from monero_income.primitives.errors import WalletUnreachableError
from tests.fakes.wallet import FakeWalletRpc, entry
from tests.integration.helpers import run_once, table

SQLITE_INTEGER_MAX = 9_223_372_036_854_775_807


def three_window_wallet() -> FakeWalletRpc:
    """Entries in each of the windows (0,10000], (10000,20000], (20000,25000]."""
    return FakeWalletRpc(
        entries=[
            entry("w1a", height=100, amount=1),
            entry("w1b", height=9_000, amount=2),
            entry("w2", height=15_000, amount=3),
            entry("w3", height=22_000, amount=4),
        ],
        height=25_000,
    )


def txids(db_path: Path) -> set[str]:
    return {row[0] for row in table(db_path)}


def test_wallet_failure_keeps_completed_windows_and_next_run_completes(tmp_path: Path) -> None:
    db_path = tmp_path / "interrupted.db"
    wallet = three_window_wallet()
    wallet.fail_on_call = 3
    wallet.failure = WalletUnreachableError("connection refused")

    with pytest.raises(RunError):
        run_once(db_path, wallet)

    w1a, w1b, w2, _ = (e["txid"] for e in wallet.entries)
    assert txids(db_path) == {w1a, w1b, w2}

    wallet.fail_on_call = None
    run_once(db_path, wallet)

    uninterrupted = tmp_path / "uninterrupted.db"
    run_once(uninterrupted, three_window_wallet())
    assert table(db_path) == table(uninterrupted)


def test_ctrl_c_keeps_window_one_and_leaves_no_lock(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    wallet = three_window_wallet()
    wallet.fail_on_call = 2
    wallet.failure = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        run_once(db_path, wallet)

    conn = open_database(db_path, timeout=0.1)  # would fail if a write lock were left behind
    conn.close()
    w1a, w1b, *_ = (e["txid"] for e in wallet.entries)
    assert txids(db_path) == {w1a, w1b}


def test_failure_inside_a_window_insert_records_nothing_from_that_window(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    wallet = three_window_wallet()
    wallet.entries.append(entry("too-big", height=23_000, amount=SQLITE_INTEGER_MAX + 1))

    with pytest.raises(RunError, match="cannot write to database"):
        run_once(db_path, wallet)

    w1a, w1b, w2, *_ = (e["txid"] for e in wallet.entries)
    assert txids(db_path) == {w1a, w1b, w2}  # neither window-3 row, windows 1-2 kept
