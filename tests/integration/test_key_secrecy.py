"""SC-008: the API key never appears in output, errors, or repr, whatever the outcome.

These tests drive the real CLI and the real run(), with only the wallet, the price
source, the clock, and sleep replaced, so every line a user would see is checked.
"""

import sqlite3
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from monero_income import cli
from monero_income.orchestration import CliOptions, Reporter, RunResult
from monero_income.orchestration import pricing as pricing_module
from monero_income.orchestration import run as run_function
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
from tests.fakes.wallet import FakeWalletRpc, entry

KEY = "CG-Zq9!distinctive-secret-key"
NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
DAY_1, DAY_2 = date(2026, 10, 10), date(2026, 10, 11)

runner = CliRunner()


def at(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp())


def wired_run(
    tmp_path: Path, prices: FakePriceSource, config_text: str | None = None
) -> Callable[[CliOptions, Reporter], RunResult]:
    """The real run(), with fakes for everything that would leave the machine or wait."""
    config = tmp_path / "config.toml"
    if config_text is not None:
        config.write_text(config_text)
        config.chmod(0o600)
    wallet = FakeWalletRpc(
        entries=[
            entry("a", height=100, amount=1, timestamp=at(DAY_1)),
            entry("b", height=101, amount=2, timestamp=at(DAY_2)),
        ],
        height=200,
    )

    def run(options: CliOptions, reporter: Reporter) -> RunResult:
        clock = FakeClock(NOW)
        return run_function(
            CliOptions(
                db_path=str(tmp_path / "xmr.db"),
                coingecko_api_key=options.coingecko_api_key,
                coingecko_api_key_type=options.coingecko_api_key_type,
            ),
            reporter,
            config_path=config,
            wallet_factory=lambda settings: wallet,
            price_source_factory=lambda settings: prices,
            clock=clock,
            sleep=RecordingSleep(clock),
        )

    return run


def prices_with(day_2: Answer | list[Answer]) -> FakePriceSource:
    return FakePriceSource({DAY_1: Price(Decimal("150")), DAY_2: day_2})


OUTCOMES: dict[str, Callable[[], FakePriceSource]] = {
    "success": lambda: prices_with(Price(Decimal("151"))),
    "rate_limited": lambda: prices_with([PriceRateLimitedError(None), PriceRateLimitedError(None)]),
    "key_rejected": lambda: prices_with(PriceKeyRejectedError()),
    "unavailable": lambda: prices_with(PriceUnavailableError("HTTP 503")),
}

KEY_SOURCES = {
    "config file": (
        f'coingecko_api_key = "{KEY}"\ncoingecko_api_key_type = "demo"\n',
        [],
    ),
    "command line": (
        None,
        ["--coingecko-api-key", KEY, "--coingecko-api-key-type", "demo"],
    ),
}


@pytest.mark.parametrize("outcome", OUTCOMES)
@pytest.mark.parametrize("key_source", KEY_SOURCES)
def test_key_never_appears_in_any_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str, key_source: str
) -> None:
    config_text, args = KEY_SOURCES[key_source]
    monkeypatch.setattr(cli, "run", wired_run(tmp_path, OUTCOMES[outcome](), config_text))

    result = runner.invoke(cli.app, args)

    assert result.exit_code == 0
    assert KEY not in result.output
    assert KEY not in result.stderr
    assert "Traceback" not in result.output
    if outcome != "success":
        assert "Warning: price lookups stopped:" in result.stderr


@pytest.mark.parametrize("key_source", KEY_SOURCES)
def test_key_never_appears_after_a_storage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key_source: str
) -> None:
    config_text, args = KEY_SOURCES[key_source]

    def failing_upsert(conn: sqlite3.Connection, price: DailyPrice) -> None:
        raise StorageWriteError("disk I/O error")

    monkeypatch.setattr(pricing_module, "upsert_price", failing_upsert)
    monkeypatch.setattr(cli, "run", wired_run(tmp_path, OUTCOMES["success"](), config_text))

    result = runner.invoke(cli.app, args)

    assert result.exit_code == 1
    assert "Error: cannot write to database" in result.stderr
    assert KEY not in result.output


@pytest.mark.parametrize(
    "config_text",
    [
        f'coingecko_api_key = "{KEY}"\n',  # key without a type
        f'coingecko_api_key = "{KEY}"\ncoingecko_api_key_type = "paid"\n',
        f'coingecko_api_key = "{KEY}"\ncoingecko_api_key_type = "demo"\n'
        f'coingecko_url = "https://u:{KEY}@api.coingecko.com/api/v3"\n',
    ],
)
def test_key_never_appears_in_config_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config_text: str
) -> None:
    monkeypatch.setattr(cli, "run", wired_run(tmp_path, OUTCOMES["success"](), config_text))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 1
    assert result.stderr.startswith("Error: invalid ")
    assert KEY not in result.output


def test_key_never_appears_in_the_result_repr(tmp_path: Path) -> None:
    run = wired_run(
        tmp_path,
        OUTCOMES["key_rejected"](),
        f'coingecko_api_key = "{KEY}"\ncoingecko_api_key_type = "pro"\n',
    )

    class Silent:
        def warning(self, message: str) -> None:
            assert KEY not in message

    result = run(CliOptions(), Silent())

    assert KEY not in repr(result)
