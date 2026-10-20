"""US4: --import-prices fills old unpriced days with final prices, then pricing continues."""

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, RunResult, run
from monero_income.primitives.database import open_database
from monero_income.primitives.errors import WalletUnreachableError
from monero_income.primitives.models import DailyPrice
from monero_income.primitives.price_parse import Price
from monero_income.primitives.prices_db import upsert_price
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)  # history cutoff: 2025-10-18
OLD_1, OLD_2, OLD_PRICED = date(2025, 3, 1), date(2025, 3, 2), date(2025, 3, 3)
RECENT_1, RECENT_2 = date(2026, 10, 1), date(2026, 10, 2)
DAYS = [OLD_1, OLD_2, OLD_PRICED, RECENT_1, RECENT_2]
CSV = (
    "date_utc,usd_price\n"
    "2025-03-01,120.5\n"
    "2025-03-02,121.25\n"
    "2025-03-03,999\n"  # already priced: skipped
    "2026-10-01,888\n"  # inside the window: skipped, priced by the source
    "2026-10-02,777\n"
)


def at(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp())


def wallet(fail: bool = False) -> FakeWalletRpc:
    fake = FakeWalletRpc(
        entries=[
            entry(day.isoformat(), height=100 + i, amount=1, timestamp=at(day))
            for i, day in enumerate(DAYS)
        ],
        height=1_000,
    )
    if fail:
        fake.fail_on_call = 1
        fake.failure = WalletUnreachableError("connection refused")
    return fake


def import_run(
    db_path: Path, csv_path: Path, prices: FakePriceSource, *, fail_sync: bool = False
) -> RunResult:
    clock = FakeClock(NOW)
    return run(
        CliOptions(db_path=str(db_path), import_prices=str(csv_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet(fail_sync),
        price_source_factory=lambda settings: prices,
        clock=clock,
        sleep=RecordingSleep(clock),
    )


def prices_table(db_path: Path) -> dict[str, tuple[str, str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        return {
            day: (price, status, source)
            for day, price, status, source in conn.execute(
                "SELECT date_utc, usd_price, status, source FROM daily_prices"
            )
        }
    finally:
        conn.close()


def recent_prices() -> FakePriceSource:
    return FakePriceSource({RECENT_1: Price(Decimal("160")), RECENT_2: Price(Decimal("161"))})


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """A database where one old day already has a price (from an earlier import or run)."""
    path = tmp_path / "xmr.db"
    conn = open_database(path)
    upsert_price(conn, DailyPrice(OLD_PRICED, Decimal("130"), "final", "import", 0))
    conn.close()
    return path


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    path = tmp_path / "prices.csv"
    path.write_text(CSV)
    return path


def test_old_unpriced_days_are_imported_and_recent_days_priced_by_the_source(
    db_path: Path, csv_path: Path
) -> None:
    prices = recent_prices()

    result = import_run(db_path, csv_path, prices)

    assert result.imported is not None
    assert (result.imported.imported, result.imported.skipped) == (2, 3)
    assert prices_table(db_path) == {
        "2025-03-01": ("120.5", "final", "import"),
        "2025-03-02": ("121.25", "final", "import"),
        "2025-03-03": ("130", "final", "import"),  # unchanged (US4-2)
        "2026-10-01": ("160", "final", "api"),
        "2026-10-02": ("161", "final", "api"),
    }
    assert prices.requests == [RECENT_1, RECENT_2]  # imported days aren't requested
    assert result.pricing.too_old == 0
    assert result.pricing.all_final


def test_bad_row_rejects_the_whole_file_before_any_lookup(db_path: Path, csv_path: Path) -> None:
    csv_path.write_text("date_utc,usd_price\n2025-03-01,120.5\n2025-03-02,1\n2025-03-04,0\n")
    before = csv_path.read_bytes()
    prices = recent_prices()

    with pytest.raises(RunError) as excinfo:
        import_run(db_path, csv_path, prices)

    message = str(excinfo.value)
    assert "cannot import prices from" in message
    assert "line 4" in message
    assert prices_table(db_path) == {"2025-03-03": ("130", "final", "import")}
    assert prices.requests == []
    assert csv_path.read_bytes() == before


def test_importing_the_same_file_again_imports_nothing(db_path: Path, csv_path: Path) -> None:
    import_run(db_path, csv_path, recent_prices())

    result = import_run(db_path, csv_path, recent_prices())

    assert result.imported is not None
    assert (result.imported.imported, result.imported.skipped) == (0, 5)


def test_failed_sync_means_no_import_and_no_lookups(db_path: Path, csv_path: Path) -> None:
    prices = recent_prices()

    with pytest.raises(RunError):
        import_run(db_path, csv_path, prices, fail_sync=True)

    assert prices_table(db_path) == {"2025-03-03": ("130", "final", "import")}
    assert prices.requests == []


def test_missing_file_is_an_error(db_path: Path, tmp_path: Path) -> None:
    with pytest.raises(RunError, match="cannot import prices from"):
        import_run(db_path, tmp_path / "nope.csv", recent_prices())


def test_without_the_option_nothing_is_imported(db_path: Path) -> None:
    clock = FakeClock(NOW)
    result = run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet(),
        price_source_factory=lambda settings: recent_prices(),
        clock=clock,
        sleep=RecordingSleep(clock),
    )

    assert result.imported is None
    assert result.pricing.too_old == 2  # OLD_1 and OLD_2 have no price
