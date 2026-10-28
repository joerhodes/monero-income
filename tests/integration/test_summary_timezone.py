"""US4: the summary time zone is --timezone, then the config file, then the machine's."""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, RunResult, run
from monero_income.orchestration.settings import Settings
from monero_income.primitives.price_parse import Price
from monero_income.primitives.wallet_rpc import WalletRpc
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

MOMENT = datetime(2026, 11, 1, 3, 30, tzinfo=UTC)  # 2026-10-31 23:30 in New York
XMR = 10**12


@pytest.fixture(autouse=True)
def machine_is_utc(local_tz: Callable[[str], None]) -> None:
    local_tz("UTC")


def tz_run(
    tmp_path: Path,
    options: CliOptions,
    config: str = "",
    now: datetime = datetime(2026, 11, 2, 12, tzinfo=UTC),
    wallet_factory: Callable[[Settings], WalletRpc] | None = None,
) -> RunResult:
    config_path = tmp_path / "config.toml"
    config_path.write_text(config)
    config_path.chmod(0o600)
    wallet = FakeWalletRpc(
        entries=[entry("a", height=100, amount=XMR, timestamp=int(MOMENT.timestamp()))],
        height=200,
    )
    clock = FakeClock(now)
    return run(
        options,
        ListReporter(),
        config_path=config_path,
        wallet_factory=wallet_factory or (lambda settings: wallet),
        price_source_factory=lambda settings: FakePriceSource({MOMENT.date(): Price(Decimal(150))}),
        clock=clock,
        sleep=RecordingSleep(clock),
    )


def month_of_the_transaction(result: RunResult) -> list[str]:
    assert result.summaries is not None
    return [p.label for p in result.summaries.monthly.periods if p.piconero]


@pytest.mark.parametrize(
    ("option", "config", "month"),
    [
        pytest.param(None, "", "2026-11", id="machine zone"),
        pytest.param(None, 'timezone = "America/New_York"\n', "2026-10", id="config file"),
        pytest.param("UTC", 'timezone = "America/New_York"\n', "2026-11", id="option wins"),
    ],
)
def test_the_zone_decides_the_period(
    tmp_path: Path, option: str | None, config: str, month: str
) -> None:
    options = CliOptions(db_path=str(tmp_path / "xmr.db"), timezone=option)

    result = tz_run(tmp_path, options, config)

    assert month_of_the_transaction(result) == [month]


def test_an_unknown_zone_fails_before_syncing(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    reports = tmp_path / "reports"
    made: list[Settings] = []

    def watched_factory(settings: Settings) -> WalletRpc:
        made.append(settings)
        return FakeWalletRpc()

    options = CliOptions(
        db_path=str(db_path), reports_path=str(reports), timezone="Mars/Olympus_Mons"
    )
    with pytest.raises(RunError) as excinfo:
        tz_run(tmp_path, options, wallet_factory=watched_factory)

    assert str(excinfo.value) == "invalid timezone: unknown time zone 'Mars/Olympus_Mons'"
    assert made == []
    assert not db_path.exists()
    assert not reports.exists()


def test_the_zone_also_decides_today(tmp_path: Path) -> None:
    options = CliOptions(db_path=str(tmp_path / "xmr.db"), timezone="America/New_York")

    result = tz_run(tmp_path, options, now=MOMENT)

    assert result.summaries is not None
    assert result.summaries.monthly.periods[-1].label == "2026-10"
    assert month_of_the_transaction(result) == ["2026-10"]
