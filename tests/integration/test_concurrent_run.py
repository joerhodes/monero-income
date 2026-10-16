"""Spec edge case: a second run while one holds the write lock fails cleanly, losing nothing."""

import sqlite3
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, run
from monero_income.primitives.database import open_database
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry
from tests.integration.helpers import run_once, table


def test_second_run_fails_with_storage_error_and_loses_nothing(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    wallet = FakeWalletRpc(entries=[entry("old", height=100, amount=1)], height=200)
    run_once(db_path, wallet)
    before = table(db_path)
    wallet.entries.append(entry("new", height=150, amount=2))

    holder = sqlite3.connect(db_path)
    holder.execute("BEGIN IMMEDIATE")  # the "first run", mid-write
    try:
        with pytest.raises(RunError) as excinfo:
            run(
                CliOptions(db_path=str(db_path)),
                ListReporter(),
                config_path=tmp_path / "absent.toml",
                wallet_factory=lambda settings: wallet,
                connect=lambda path: open_database(path, timeout=0.1),
            )
    finally:
        holder.rollback()
        holder.close()

    message = str(excinfo.value)
    assert "cannot write to database" in message or "cannot read database" in message
    assert table(db_path) == before
