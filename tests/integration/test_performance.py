"""SC-006: a run with nothing new, over 10,000 recorded rows, takes under 5 seconds."""

import time
from pathlib import Path

from monero_income.primitives.database import insert_records, open_database
from monero_income.primitives.models import TransactionRecord
from tests.fakes.wallet import FakeWalletRpc
from tests.integration.helpers import run_once


def test_nothing_new_over_10000_rows_is_fast(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    conn = open_database(db_path)
    insert_records(
        conn,
        [
            TransactionRecord(
                txid=f"{height:064x}", height=height, amount_piconero=1, occurred_at=height
            )
            for height in range(1, 10_001)
        ],
    )
    conn.close()

    start = time.perf_counter()
    result = run_once(db_path, FakeWalletRpc(height=20_000))  # the fake answers instantly
    elapsed = time.perf_counter() - start

    assert result.recorded == 0
    assert elapsed < 5.0
