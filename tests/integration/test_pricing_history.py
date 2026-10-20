"""US3: days older than the price history are never requested and are reported apart."""

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from monero_income.orchestration import CliOptions, RunResult, run
from monero_income.primitives.price_parse import OutsideHistory, Price
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

TODAY_NOON = datetime(2026, 10, 17, 12, tzinfo=UTC)


def at(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp())


def price_run(
    db_path: Path, days: list[date], prices: FakePriceSource, clock: FakeClock
) -> RunResult:
    wallet = FakeWalletRpc(
        entries=[
            entry(day.isoformat(), height=100 + i, amount=1, timestamp=at(day))
            for i, day in enumerate(days)
        ],
        height=1_000,
    )
    return run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet,
        price_source_factory=lambda settings: prices,
        clock=clock,
        sleep=RecordingSleep(clock),
    )


def status_of(db_path: Path, day: date) -> str | None:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT status FROM daily_prices WHERE date_utc = ?", (day.isoformat(),)
        ).fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def test_only_days_inside_the_364_day_window_are_requested(tmp_path: Path) -> None:
    old, inside = date(2025, 10, 17), date(2025, 10, 18)  # 365 and 364 days old
    prices = FakePriceSource({old: Price(Decimal("1")), inside: Price(Decimal("2"))})

    result = price_run(tmp_path / "xmr.db", [old, inside], prices, FakeClock(TODAY_NOON))

    assert prices.requests == [inside]  # SC-006: nothing requested for the old day
    assert result.pricing.too_old == 1
    assert result.pricing.priced == 1


def test_provisional_day_that_aged_out_is_not_requested_and_stays_provisional(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "xmr.db"
    day = date(2025, 10, 16)
    clock = FakeClock(datetime(2025, 10, 16, 18, tzinfo=UTC))
    price_run(db_path, [day], FakePriceSource({day: Price(Decimal("150"))}), clock)
    assert status_of(db_path, day) == "provisional"

    clock.now = TODAY_NOON  # the tool wasn't run for a year
    later = FakePriceSource({day: Price(Decimal("999"))})
    result = price_run(db_path, [day], later, clock)

    assert later.requests == []
    assert status_of(db_path, day) == "provisional"
    assert result.pricing.too_old == 1
    assert result.pricing.not_refreshed == 0


def test_outside_history_answer_counts_too_old_and_pricing_continues(tmp_path: Path) -> None:
    edge, newer = date(2025, 10, 18), date(2026, 3, 1)
    prices = FakePriceSource({edge: OutsideHistory(), newer: Price(Decimal("160"))})

    result = price_run(tmp_path / "xmr.db", [edge, newer], prices, FakeClock(TODAY_NOON))

    assert prices.requests == [edge, newer]
    assert result.pricing.too_old == 1
    assert result.pricing.priced == 1
    assert result.pricing.stopped is None


def test_too_old_no_price_and_not_refreshed_are_counted_separately(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    old, missing, recent = date(2025, 10, 1), date(2026, 1, 1), date(2026, 10, 16)
    days = [old, missing, recent]
    clock = FakeClock(datetime(2026, 10, 16, 18, tzinfo=UTC))
    price_run(db_path, days, FakePriceSource({recent: Price(Decimal("150"))}), clock)
    assert status_of(db_path, recent) == "provisional"

    clock.now = TODAY_NOON
    result = price_run(db_path, days, FakePriceSource(), clock)  # answers "no price" for all

    assert result.pricing.too_old == 1  # old
    assert result.pricing.no_price == 1  # missing
    assert result.pricing.not_refreshed == 1  # recent, still provisional
    assert status_of(db_path, recent) == "provisional"
