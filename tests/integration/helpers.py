"""Shared helpers for tests that call run() against a tmp_path database file."""

import sqlite3
from pathlib import Path

from monero_income.orchestration import CliOptions, SyncResult, run
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc

Row = tuple[str, int, int, int, str]


def run_once(db_path: Path, wallet: FakeWalletRpc, config_path: Path | None = None) -> SyncResult:
    return run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=config_path if config_path is not None else db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet,
    )


def table(db_path: Path) -> list[Row]:
    """Every stored row, in txid order: the whole observable state of the database."""
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT txid, height, amount_piconero, occurred_at, occurred_date"
            " FROM transactions ORDER BY txid"
        ).fetchall()
    finally:
        conn.close()
