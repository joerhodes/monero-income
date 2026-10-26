"""The export's bytes, locked by golden files (constitution: report output; research R8).

The golden files were written by hand from contracts/export-csv.md, not copied from the
tool's output. Any change to them must be stated in a spec.
"""

import hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from monero_income.orchestration import CliOptions, run
from monero_income.primitives.database import insert_records, open_database
from monero_income.primitives.models import DailyPrice, TransactionRecord
from monero_income.primitives.prices_db import insert_imported, upsert_price
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc

GOLDEN = Path(__file__).parent.parent / "golden"
NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)  # every day below is inside the price history
FETCHED = int(datetime(2026, 10, 26, 2, tzinfo=UTC).timestamp())


def tx(seed: str, height: int, moment: str, amount: int) -> TransactionRecord:
    occurred_at = int(datetime.fromisoformat(moment).replace(tzinfo=UTC).timestamp())
    return TransactionRecord(hashlib.sha256(seed.encode()).hexdigest(), height, amount, occurred_at)


def price(
    day: str, text: str, status: Literal["provisional", "final"], source: Literal["api", "import"]
) -> DailyPrice:
    return DailyPrice(date.fromisoformat(day), Decimal(text), status, source, FETCHED)


# Inserted out of export order, so the export's own sorting is what's tested.
TRANSACTIONS = [
    tx("golden-6", 3_539_000, "2026-10-25T11:00:00", 2_000_000_000_000),  # provisional day
    tx("golden-5", 3_532_100, "2026-10-20T18:45:10", 731_000_000_000),  # unpriced day
    tx("golden-8", 3_532_200, "2026-10-20T12:00:00", 250_000_000_000),  # later block, earlier
    tx("golden-2", 3_530_700, "2026-10-18T09:12:44", 1_000_000_000_000),  # half a cent
    tx("golden-7", 3_530_699, "2026-10-18T09:12:44", 500_000_000_000),  # same second as -2
    tx("golden-4", 3_531_450, "2026-10-19T02:30:00", 1_234_500_000_000_000),  # over 100,000 USD
    tx("golden-3", 3_531_400, "2026-10-19T00:00:00", 1),  # 1 piconero
    tx("golden-1", 3_530_000, "2026-10-17T14:03:05", 1_234_567_890_123),
]


def export_run(db_path: Path, wallet_height: int) -> Path:
    clock = FakeClock(NOW)
    result = run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: FakeWalletRpc(height=wallet_height),
        # Answers NoPrice for every day: the provisional price is kept, the unpriced day stays TBD.
        price_source_factory=lambda settings: FakePriceSource(),
        clock=clock,
        sleep=RecordingSleep(clock),
    )
    assert result.exported is not None
    return result.exported.path


def test_export_matches_the_golden_file(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    conn = open_database(db_path)
    try:
        insert_records(conn, TRANSACTIONS)
        upsert_price(conn, price("2026-10-17", "152.3456", "final", "api"))
        upsert_price(conn, price("2026-10-18", "152.345", "final", "api"))
        insert_imported(conn, [price("2026-10-19", "150", "final", "import")])
        upsert_price(conn, price("2026-10-25", "163.40000000000001", "provisional", "api"))
    finally:
        conn.close()

    path = export_run(db_path, wallet_height=3_539_000)

    assert path.read_bytes() == (GOLDEN / "xmr_income.csv").read_bytes()


def test_empty_export_matches_the_golden_file(tmp_path: Path) -> None:
    path = export_run(tmp_path / "xmr.db", wallet_height=0)

    assert path.read_bytes() == (GOLDEN / "xmr_income_empty.csv").read_bytes()
