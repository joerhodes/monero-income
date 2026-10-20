"""US1: after a successful sync, days are priced and transactions valued exactly."""

import sqlite3
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, RunResult, run
from monero_income.orchestration.valuation import usd_value
from monero_income.primitives.errors import WalletUnreachableError
from monero_income.primitives.price_parse import Price
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
D1, D2, D3 = date(2026, 10, 10), date(2026, 10, 12), date(2026, 10, 17)  # D3 is today


def at(day: date, hour: int = 12) -> int:
    return int(datetime(day.year, day.month, day.day, hour, tzinfo=UTC).timestamp())


def price_run(
    db_path: Path,
    wallet: FakeWalletRpc,
    prices: FakePriceSource,
    clock: FakeClock,
) -> RunResult:
    return run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet,
        price_source_factory=lambda settings: prices,
        clock=clock,
        sleep=RecordingSleep(clock),
    )


def prices_table(db_path: Path) -> dict[date, tuple[Decimal, str, str]]:
    conn = sqlite3.connect(db_path)
    try:
        return {
            date.fromisoformat(day): (Decimal(text), status, source)
            for day, text, status, source in conn.execute(
                "SELECT date_utc, usd_price, status, source FROM daily_prices"
            )
        }
    finally:
        conn.close()


def valuations(db_path: Path) -> dict[str, Decimal]:
    """USD value of every transaction whose day has a price, computed as the tool does."""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT t.txid, t.amount_piconero, p.usd_price FROM transactions AS t"
            " JOIN daily_prices AS p ON p.date_utc = t.occurred_date"
        ).fetchall()
    finally:
        conn.close()
    return {txid: usd_value(amount, Decimal(price)) for txid, amount, price in rows}


@pytest.fixture
def wallet() -> FakeWalletRpc:
    return FakeWalletRpc(
        entries=[
            entry("a", height=100, amount=1_234_567_890_123, timestamp=at(D1)),
            entry("b", height=200, amount=500_000_000_000, timestamp=at(D2, 3)),
            entry("c", height=201, amount=250_000_000_000, timestamp=at(D2, 22)),
            entry("d", height=300, amount=1_000_000_000_000, timestamp=at(D3, 9)),
        ],
        height=400,
    )


def all_prices() -> FakePriceSource:
    return FakePriceSource(
        {
            D1: Price(Decimal("152.3456")),
            D2: Price(Decimal("160")),
            D3: Price(Decimal("161.5")),
        }
    )


def test_every_transaction_day_is_priced_and_valued_exactly(
    tmp_path: Path, wallet: FakeWalletRpc
) -> None:
    db_path = tmp_path / "xmr.db"
    prices = all_prices()

    result = price_run(db_path, wallet, prices, FakeClock(NOW))

    assert prices.requests == [D1, D2, D3]  # oldest first (FR-024)
    stored = prices_table(db_path)
    assert stored == {
        D1: (Decimal("152.3456"), "final", "api"),
        D2: (Decimal("160"), "final", "api"),
        D3: (Decimal("161.5"), "provisional", "api"),  # today hasn't settled (US1-7)
    }
    values = valuations(db_path)
    a, b, c, _ = (e["txid"] for e in wallet.entries)
    assert values[a] == Decimal("188.0809859615225088")  # US1-3
    assert values[b] == Decimal("80") and values[c] == Decimal("40")  # same day, same price
    assert result.recorded == 4
    assert (result.pricing.priced, result.pricing.provisional) == (3, 1)
    assert not result.pricing.all_final  # today is still provisional


def test_final_days_are_never_requested_again(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    wallet = FakeWalletRpc(entries=[entry("a", height=100, amount=1, timestamp=at(D1))], height=200)
    price_run(db_path, wallet, FakePriceSource({D1: Price(Decimal("150"))}), FakeClock(NOW))

    second = FakePriceSource({D1: Price(Decimal("999"))})
    result = price_run(db_path, wallet, second, FakeClock(NOW))

    assert second.requests == []
    assert prices_table(db_path)[D1] == (Decimal("150"), "final", "api")
    assert result.pricing.all_final  # US1-6
    assert result.pricing.priced == 0


def test_no_prices_are_looked_up_when_the_sync_fails(tmp_path: Path, wallet: FakeWalletRpc) -> None:
    wallet.fail_on_call = 1
    wallet.failure = WalletUnreachableError("connection refused")
    prices = all_prices()

    with pytest.raises(RunError):
        price_run(tmp_path / "xmr.db", wallet, prices, FakeClock(NOW))

    assert prices.requests == []  # US1-5, FR-002


def test_provisional_price_is_refreshed_then_finalized_by_a_later_lookup(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    day = date(2026, 10, 16)
    wallet = FakeWalletRpc(
        entries=[entry("a", height=100, amount=1, timestamp=at(day))], height=200
    )
    clock = FakeClock(datetime(2026, 10, 16, 18, tzinfo=UTC))
    price_run(db_path, wallet, FakePriceSource({day: Price(Decimal("150"))}), clock)
    assert prices_table(db_path)[day] == (Decimal("150"), "provisional", "api")

    # Time passing without a run changes nothing (SC-009).
    clock.now = datetime(2026, 10, 25, tzinfo=UTC)
    assert prices_table(db_path)[day][1] == "provisional"

    # Before settling (01:00 UTC the next day): refreshed, still provisional (US1-8).
    clock.now = datetime(2026, 10, 17, 0, 30, tzinfo=UTC)
    refresh = FakePriceSource({day: Price(Decimal("151"))})
    price_run(db_path, wallet, refresh, clock)
    assert refresh.requests == [day]
    assert prices_table(db_path)[day] == (Decimal("151"), "provisional", "api")

    # Days later: looked up once more and finalized (US1-9).
    clock.now = datetime(2026, 10, 25, 9, tzinfo=UTC)
    finalize = FakePriceSource({day: Price(Decimal("152"))})
    result = price_run(db_path, wallet, finalize, clock)
    assert finalize.requests == [day]
    assert prices_table(db_path)[day] == (Decimal("152"), "final", "api")
    assert (result.pricing.priced, result.pricing.provisional) == (1, 0)
    assert result.pricing.all_final

    # Final from then on: no more lookups.
    after = FakePriceSource({day: Price(Decimal("999"))})
    price_run(db_path, wallet, after, clock)
    assert after.requests == []


def test_empty_database_is_never_all_valued(tmp_path: Path) -> None:
    result = price_run(
        tmp_path / "xmr.db", FakeWalletRpc(height=10), FakePriceSource(), FakeClock(NOW)
    )

    assert result.recorded == 0
    assert not result.pricing.all_final
