"""US1: every run whose sync and pricing complete writes the export; a failed run writes none."""

import hashlib
import importlib
import sqlite3
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, ExportSummary, RunError, RunResult, run
from monero_income.orchestration import pricing as pricing_module
from monero_income.primitives.errors import (
    PriceUnavailableError,
    StorageWriteError,
    WalletUnreachableError,
)
from monero_income.primitives.models import DailyPrice
from monero_income.primitives.price_parse import Price
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry
from tests.integration.helpers import table

# The package re-exports the run() function under the module's name, so import the module itself.
run_module = importlib.import_module("monero_income.orchestration.run")

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
D1, D2, D3 = date(2026, 10, 10), date(2026, 10, 12), date(2026, 10, 17)  # D3 is today
HEADER = "txid,height,timestamp_utc,xmr,usd_price,price_status,usd_value\n"
OLD_EXPORT = b"txid,height\nprevious export,1\n"


def at(day: date, hour: int = 12) -> int:
    return int(datetime(day.year, day.month, day.day, hour, tzinfo=UTC).timestamp())


def txid(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def price_run(
    db_path: Path,
    wallet: FakeWalletRpc,
    prices: FakePriceSource,
    clock: FakeClock | None = None,
    options: CliOptions | None = None,
) -> RunResult:
    clock = clock or FakeClock(NOW)
    return run(
        options or CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet,
        price_source_factory=lambda settings: prices,
        clock=clock,
        sleep=RecordingSleep(clock),
    )


def three_transactions() -> FakeWalletRpc:
    return FakeWalletRpc(
        entries=[
            entry("a", height=100, amount=1_234_567_890_123, timestamp=at(D1)),
            entry("c", height=201, amount=250_000_000_000, timestamp=at(D2, 22)),
            entry("b", height=200, amount=731_000_000_000, timestamp=at(D2, 3)),
        ],
        height=300,
    )


def export_path(home: Path) -> Path:
    return home / "reports" / "xmr_income.csv"


def prices_rows(db_path: Path) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT * FROM daily_prices ORDER BY date_utc").fetchall()
    finally:
        conn.close()


def plant_old_export(home: Path) -> Path:
    path = export_path(home)
    path.parent.mkdir(parents=True)
    path.write_bytes(OLD_EXPORT)
    return path


def test_run_writes_every_transaction_oldest_first(tmp_path: Path, isolated_home: Path) -> None:
    prices = FakePriceSource({D1: Price(Decimal("152.3456"))})  # D2 has no price

    result = price_run(tmp_path / "xmr.db", three_transactions(), prices)

    path = export_path(isolated_home)
    assert path.read_text() == (
        HEADER
        + f"{txid('a')},100,2026-10-10T12:00:00Z,1.234567890123,152.3456,final,188.08\n"
        + f"{txid('b')},200,2026-10-12T03:00:00Z,0.731000000000,TBD,TBD,TBD\n"
        + f"{txid('c')},201,2026-10-12T22:00:00Z,0.250000000000,TBD,TBD,TBD\n"
    )
    assert result.exported == ExportSummary(path=path, transactions=3)
    assert path.is_absolute()


def test_provisional_day_shows_provisional_and_its_value(
    tmp_path: Path, isolated_home: Path
) -> None:
    wallet = FakeWalletRpc(
        entries=[entry("d", height=300, amount=1_000_000_000_000, timestamp=at(D3, 9))],
        height=400,
    )

    price_run(tmp_path / "xmr.db", wallet, FakePriceSource({D3: Price(Decimal("150"))}))

    (row,) = export_path(isolated_home).read_text().splitlines()[1:]
    assert row.endswith(",1.000000000000,150,provisional,150.00")


def test_price_source_failure_still_exports_with_tbd(tmp_path: Path, isolated_home: Path) -> None:
    prices = FakePriceSource({D1: PriceUnavailableError("cannot connect")})

    result = price_run(tmp_path / "xmr.db", three_transactions(), prices)

    rows = export_path(isolated_home).read_text().splitlines()[1:]
    assert len(rows) == 3
    assert all(row.endswith(",TBD,TBD,TBD") for row in rows)
    assert result.exported is not None
    assert result.exported.transactions == 3


def test_sync_failure_writes_no_export(tmp_path: Path, isolated_home: Path) -> None:
    wallet = three_transactions()
    wallet.fail_on_call = 1
    wallet.failure = WalletUnreachableError("connection refused")

    with pytest.raises(RunError):
        price_run(tmp_path / "xmr.db", wallet, FakePriceSource())

    assert not export_path(isolated_home).exists()


def test_sync_failure_leaves_the_previous_export_unchanged(
    tmp_path: Path, isolated_home: Path
) -> None:
    path = plant_old_export(isolated_home)
    wallet = three_transactions()
    wallet.fail_on_call = 1
    wallet.failure = WalletUnreachableError("connection refused")

    with pytest.raises(RunError):
        price_run(tmp_path / "xmr.db", wallet, FakePriceSource())

    assert path.read_bytes() == OLD_EXPORT


def test_invalid_import_file_leaves_the_previous_export_unchanged(
    tmp_path: Path, isolated_home: Path
) -> None:
    path = plant_old_export(isolated_home)
    db_path = tmp_path / "xmr.db"
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text("date_utc,usd_price\nnot-a-date,1\n")

    with pytest.raises(RunError, match="cannot import prices from"):
        price_run(
            db_path,
            three_transactions(),
            FakePriceSource(),
            options=CliOptions(db_path=str(db_path), import_prices=str(csv_path)),
        )

    assert path.read_bytes() == OLD_EXPORT


def test_storage_error_during_pricing_leaves_the_previous_export_unchanged(
    tmp_path: Path, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = plant_old_export(isolated_home)

    def failing_upsert(conn: sqlite3.Connection, price: DailyPrice) -> None:
        raise StorageWriteError("disk I/O error")

    monkeypatch.setattr(pricing_module, "upsert_price", failing_upsert)

    with pytest.raises(RunError, match="cannot write to database"):
        price_run(
            tmp_path / "xmr.db",
            three_transactions(),
            FakePriceSource({D1: Price(Decimal("152.3456"))}),
        )

    assert path.read_bytes() == OLD_EXPORT


def test_no_transactions_writes_the_header_only(tmp_path: Path, isolated_home: Path) -> None:
    result = price_run(tmp_path / "xmr.db", FakeWalletRpc(), FakePriceSource())

    path = export_path(isolated_home)
    assert path.read_text() == HEADER
    assert result.exported == ExportSummary(path=path, transactions=0)


def test_export_includes_prices_recorded_in_the_same_run(
    tmp_path: Path, isolated_home: Path
) -> None:
    db_path = tmp_path / "xmr.db"
    price_run(db_path, three_transactions(), FakePriceSource())
    first = export_path(isolated_home).read_text()

    price_run(db_path, three_transactions(), FakePriceSource({D2: Price(Decimal("160"))}))

    assert f"{txid('b')},200,2026-10-12T03:00:00Z,0.731000000000,TBD,TBD,TBD" in first
    assert f"{txid('b')},200,2026-10-12T03:00:00Z,0.731000000000,160,final,116.96" in (
        export_path(isolated_home).read_text()
    )


def test_runs_with_nothing_new_write_identical_files(tmp_path: Path, isolated_home: Path) -> None:
    db_path = tmp_path / "xmr.db"
    prices = FakePriceSource({D1: Price(Decimal("152.3456"))})
    price_run(db_path, three_transactions(), prices)
    first = export_path(isolated_home).read_bytes()

    price_run(db_path, three_transactions(), prices)

    assert export_path(isolated_home).read_bytes() == first


def test_export_step_changes_nothing_in_the_database(
    tmp_path: Path, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "xmr.db"
    real_read: Callable[[sqlite3.Connection], object] = run_module.read_export_rows
    snapshots: list[tuple[object, ...]] = []

    def watched_read(conn: sqlite3.Connection) -> object:
        before = (conn.total_changes, table(db_path), prices_rows(db_path))
        rows = real_read(conn)
        snapshots.append((before, (conn.total_changes, table(db_path), prices_rows(db_path))))
        return rows

    monkeypatch.setattr(run_module, "read_export_rows", watched_read)

    price_run(db_path, three_transactions(), FakePriceSource({D1: Price(Decimal("152.3456"))}))

    ((before, after),) = snapshots
    assert before == after
    assert export_path(isolated_home).is_file()
