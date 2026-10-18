"""US2: pacing, one retry on a rate limit, clean stops, and storage errors that fail the run."""

import sqlite3
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, RunResult, run
from monero_income.orchestration import pricing as pricing_module
from monero_income.primitives import prices_db
from monero_income.primitives.errors import (
    PriceKeyRejectedError,
    PriceRateLimitedError,
    PriceUnavailableError,
    StorageWriteError,
)
from monero_income.primitives.models import DailyPrice
from monero_income.primitives.price_parse import Price
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import Answer, FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
DAYS = [date(2026, 10, 1) + timedelta(days=offset) for offset in range(10)]


def at(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp())


def wallet_for(days: list[date]) -> FakeWalletRpc:
    return FakeWalletRpc(
        entries=[
            entry(day.isoformat(), height=100 + i, amount=1, timestamp=at(day))
            for i, day in enumerate(days)
        ],
        height=1_000,
    )


def price_for(day: date) -> Price:
    return Price(Decimal(100 + day.day) + Decimal("0.25"))


def answers(days: list[date]) -> FakePriceSource:
    mapping: dict[date, Answer | list[Answer]] = {day: price_for(day) for day in days}
    return FakePriceSource(mapping)


def price_run(
    db_path: Path,
    prices: FakePriceSource,
    *,
    days: list[date] = DAYS,
    clock: FakeClock | None = None,
    sleep: RecordingSleep | None = None,
    options: CliOptions | None = None,
) -> RunResult:
    clock = clock or FakeClock(NOW)
    return run(
        options or CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet_for(days),
        price_source_factory=lambda settings: prices,
        clock=clock,
        sleep=sleep or RecordingSleep(clock),
    )


def prices_table(db_path: Path) -> list[tuple[str, str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT date_utc, usd_price, status FROM daily_prices ORDER BY date_utc"
        ).fetchall()
    finally:
        conn.close()


def uninterrupted_table(tmp_path: Path) -> list[tuple[str, str, str]]:
    fresh = tmp_path / "uninterrupted" / "xmr.db"
    fresh.parent.mkdir()
    price_run(fresh, answers(DAYS))
    return prices_table(fresh)


def priced_dates(db_path: Path) -> list[date]:
    return [date.fromisoformat(row[0]) for row in prices_table(db_path)]


def test_source_failure_keeps_prices_and_the_next_run_requests_the_rest(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    first = answers(DAYS)
    first.answers[DAYS[4]] = PriceUnavailableError("HTTP 503")

    result = price_run(db_path, first)

    assert first.requests == DAYS[:5]
    assert priced_dates(db_path) == DAYS[:4]
    assert result.pricing.priced == 4
    assert result.pricing.no_price == 6
    assert result.pricing.stopped is not None
    assert result.pricing.stopped.kind == "unavailable"
    assert "HTTP 503" in result.pricing.stopped.reason
    assert max(priced_dates(db_path)) < DAYS[4]  # SC-010: priced days are all older

    second = answers(DAYS)
    price_run(db_path, second)

    assert second.requests == DAYS[4:]
    assert prices_table(db_path) == uninterrupted_table(tmp_path)  # SC-005


def test_rate_limit_is_retried_once_after_a_backoff(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    clock = FakeClock(NOW)
    sleep = RecordingSleep(clock)
    prices = answers(DAYS[:3])
    prices.answers[DAYS[1]] = [PriceRateLimitedError(None), price_for(DAYS[1])]

    result = price_run(db_path, prices, days=DAYS[:3], clock=clock, sleep=sleep)

    assert prices.requests == [DAYS[0], DAYS[1], DAYS[1], DAYS[2]]
    assert 10.0 in sleep.calls
    assert result.pricing.priced == 3
    assert result.pricing.stopped is None


def test_second_rate_limit_stops_pricing_with_no_further_requests(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    prices = answers(DAYS)
    prices.answers[DAYS[2]] = [PriceRateLimitedError(None), PriceRateLimitedError(None)]

    result = price_run(db_path, prices)

    assert prices.requests == [DAYS[0], DAYS[1], DAYS[2], DAYS[2]]  # SC-011
    assert result.pricing.stopped is not None
    assert result.pricing.stopped.kind == "rate_limited"
    assert result.pricing.priced == 2
    assert result.pricing.no_price == 8


@pytest.mark.parametrize(("retry_after", "slept"), [(30.0, 30.0), (120.0, 60.0)])
def test_retry_after_is_honoured_up_to_60_seconds(
    tmp_path: Path, retry_after: float, slept: float
) -> None:
    clock = FakeClock(NOW)
    sleep = RecordingSleep(clock)
    prices = answers(DAYS[:1])
    prices.answers[DAYS[0]] = [PriceRateLimitedError(retry_after), price_for(DAYS[0])]

    price_run(tmp_path / "xmr.db", prices, days=DAYS[:1], clock=clock, sleep=sleep)

    assert sleep.calls == [slept]


def test_ctrl_c_keeps_recorded_prices_and_the_next_run_requests_the_rest(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    first = answers(DAYS)
    first.answers[DAYS[2]] = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        price_run(db_path, first)

    assert priced_dates(db_path) == DAYS[:2]

    second = answers(DAYS)
    price_run(db_path, second)

    assert second.requests == DAYS[2:]
    assert prices_table(db_path) == uninterrupted_table(tmp_path)  # SC-005


@pytest.mark.parametrize(
    ("options", "minimum"),
    [
        (CliOptions(coingecko_api_key="CG-x", coingecko_api_key_type="demo"), 2.5),
        (CliOptions(), 6.0),
    ],
)
def test_requests_are_paced(tmp_path: Path, options: CliOptions, minimum: float) -> None:
    db_path = tmp_path / "xmr.db"
    clock = FakeClock(NOW)
    sleep = RecordingSleep(clock)
    prices = answers(DAYS[:4])
    options = CliOptions(
        db_path=str(db_path),
        coingecko_api_key=options.coingecko_api_key,
        coingecko_api_key_type=options.coingecko_api_key_type,
    )

    price_run(db_path, prices, days=DAYS[:4], clock=clock, sleep=sleep, options=options)

    assert len(sleep.calls) == 3  # none before the first request
    assert all(seconds >= minimum for seconds in sleep.calls)


def test_min_request_delay_overrides_the_default(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    config = tmp_path / "config.toml"
    config.write_text("min_request_delay = 2\n")
    config.chmod(0o600)
    clock = FakeClock(NOW)
    sleep = RecordingSleep(clock)

    run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=config,
        wallet_factory=lambda settings: wallet_for(DAYS[:3]),
        price_source_factory=lambda settings: answers(DAYS[:3]),
        clock=clock,
        sleep=sleep,
    )

    assert sleep.calls == [2.0, 2.0]


def test_unreachable_source_from_the_start_still_returns_the_sync_count(tmp_path: Path) -> None:
    prices = FakePriceSource({DAYS[0]: PriceUnavailableError("cannot connect")})

    result = price_run(tmp_path / "xmr.db", prices)

    assert result.recorded == 10
    assert result.pricing.stopped is not None
    assert result.pricing.stopped.kind == "unavailable"
    assert result.pricing.priced == 0
    assert result.pricing.no_price == 10


def test_rejected_key_stops_pricing(tmp_path: Path) -> None:
    prices = answers(DAYS)
    prices.answers[DAYS[3]] = PriceKeyRejectedError()

    result = price_run(tmp_path / "xmr.db", prices)

    assert result.pricing.stopped is not None
    assert result.pricing.stopped.kind == "key_rejected"
    assert result.pricing.priced == 3


def test_storage_error_during_pricing_fails_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "xmr.db"
    real_upsert: Callable[[sqlite3.Connection, DailyPrice], None] = prices_db.upsert_price
    calls: list[date] = []

    def failing_upsert(conn: sqlite3.Connection, price: DailyPrice) -> None:
        calls.append(price.date_utc)
        if len(calls) == 3:
            raise StorageWriteError("disk I/O error")
        real_upsert(conn, price)

    monkeypatch.setattr(pricing_module, "upsert_price", failing_upsert)

    with pytest.raises(RunError, match="cannot write to database"):
        price_run(db_path, answers(DAYS))

    assert priced_dates(db_path) == DAYS[:2]  # FR-025: earlier prices kept


def test_failed_refresh_keeps_the_provisional_price(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    day = date(2026, 10, 16)
    clock = FakeClock(datetime(2026, 10, 16, 18, tzinfo=UTC))
    price_run(db_path, FakePriceSource({day: Price(Decimal("150"))}), days=[day], clock=clock)

    clock.now = datetime(2026, 10, 25, tzinfo=UTC)
    result = price_run(
        db_path,
        FakePriceSource({day: PriceUnavailableError("HTTP 502")}),
        days=[day],
        clock=clock,
    )

    assert prices_table(db_path) == [("2026-10-16", "150", "provisional")]  # FR-023
    assert result.pricing.not_refreshed == 1
    assert result.pricing.no_price == 0
