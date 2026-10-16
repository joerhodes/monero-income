"""US1: a first run records every incoming transaction exactly (run() with fakes)."""

import sqlite3
from pathlib import Path

from monero_income.orchestration import CliOptions, run
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry


def stored(db_path: Path) -> dict[str, tuple[int, int, int, str]]:
    conn = sqlite3.connect(db_path)
    try:
        return {
            txid: (height, amount, occurred_at, occurred_date)
            for txid, height, amount, occurred_at, occurred_date in conn.execute(
                "SELECT txid, height, amount_piconero, occurred_at, occurred_date FROM transactions"
            )
        }
    finally:
        conn.close()


def test_first_run_records_every_incoming_transaction_exactly(tmp_path: Path) -> None:
    single = entry("single", height=5, amount=123456789012, timestamp=1704067199)
    boundary = entry("boundary", height=10000, amount=1_000_000_000_000, timestamp=1704067200)
    split_a = entry("split", height=10001, amount=400000000000, timestamp=1704153600)
    split_b = entry(
        "split", height=10001, amount=600000000001, timestamp=1704153600, subaddr_minor=1
    )
    late = entry("late", height=24999, amount=7, timestamp=1704240000)
    wallet = FakeWalletRpc(entries=[single, boundary, split_a, split_b, late], height=25000)
    db_path = tmp_path / "data" / "xmr.db"

    result = run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=tmp_path / "absent.toml",
        wallet_factory=lambda settings: wallet,
    )

    assert result.recorded == 4
    assert stored(db_path) == {
        single["txid"]: (5, 123456789012, 1704067199, "2023-12-31"),
        boundary["txid"]: (10000, 1_000_000_000_000, 1704067200, "2024-01-01"),
        split_a["txid"]: (10001, 1_000_000_000_001, 1704153600, "2024-01-02"),
        late["txid"]: (24999, 7, 1704240000, "2024-01-03"),
    }
    assert wallet.calls == [(0, 10000), (10000, 20000), (20000, 25000)]

    # FR-003 / US1 scenario 2 (only incoming recorded) is covered by the "out": false
    # assertion in tests/adapters/test_wallet_rpc_http.py; the fake holds only incoming entries.
