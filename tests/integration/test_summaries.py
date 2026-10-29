"""US1: every successful run builds the income summaries from the same data as the export."""

import csv
import importlib
import sqlite3
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, RunResult, SummaryError, run
from monero_income.orchestration.export import ExportSummary
from monero_income.orchestration.summary import IncomeSummaries, build_summaries
from monero_income.primitives.errors import WalletUnreachableError
from monero_income.primitives.export_db import export_records
from monero_income.primitives.models import ExportRecord
from monero_income.primitives.price_parse import Price
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

# The package re-exports the run() function under the module's name, so import the module itself.
run_module = importlib.import_module("monero_income.orchestration.run")

NOW = datetime(2026, 10, 27, 15, tzinfo=UTC)
TODAY = date(2026, 10, 27)
D1, D2, D3 = date(2026, 6, 10), date(2026, 9, 30), date(2026, 10, 20)


def at(day: date, hour: int = 12) -> int:
    return int(datetime(day.year, day.month, day.day, hour, tzinfo=UTC).timestamp())


def wallet() -> FakeWalletRpc:
    return FakeWalletRpc(
        entries=[
            entry("a", height=100, amount=1_234_500_000_000_000, timestamp=at(D1)),
            entry("b", height=200, amount=731_000_000_000, timestamp=at(D2, 3)),
            entry("c", height=300, amount=250_000_000_000, timestamp=at(D3)),
        ],
        height=400,
    )


def prices() -> FakePriceSource:
    return FakePriceSource({D1: Price(Decimal("152.345")), D2: Price(Decimal("158.5"))})


def summary_run(
    db_path: Path,
    wallet: FakeWalletRpc,
    options: CliOptions | None = None,
    summary_reader: Callable[[sqlite3.Connection], Sequence[ExportRecord]] = export_records,
) -> RunResult:
    clock = FakeClock(NOW)
    return run(
        options or CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: wallet,
        price_source_factory=lambda settings: prices(),
        clock=clock,
        sleep=RecordingSleep(clock),
        summary_reader=summary_reader,
    )


def prices_rows(db_path: Path) -> list[tuple[object, ...]]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT * FROM daily_prices ORDER BY date_utc").fetchall()
    finally:
        conn.close()


def records(db_path: Path) -> list[ExportRecord]:
    conn = sqlite3.connect(db_path)
    try:
        return export_records(conn)
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def new_york(local_tz: Callable[[str], None]) -> None:
    local_tz("America/New_York")


def test_a_successful_run_sets_the_summaries(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"

    result = summary_run(db_path, wallet())

    assert result.summaries is not None
    assert result.summaries == build_summaries(records(db_path), TODAY, None)
    assert result.summaries.transactions == 3


def test_the_summaries_hold_the_same_transactions_as_the_export(tmp_path: Path) -> None:
    result = summary_run(tmp_path / "xmr.db", wallet())

    assert result.exported is not None
    assert result.summaries is not None
    with result.exported.path.open(newline="") as file:
        exported = sum(Decimal(row["xmr"]) for row in csv.DictReader(file))
    # Every transaction is within the last 26 weeks, so the weekly total holds them all.
    assert Decimal(result.summaries.weekly.total.piconero).scaleb(-12) == exported


def test_no_transactions_gives_an_empty_count(tmp_path: Path) -> None:
    result = summary_run(tmp_path / "xmr.db", FakeWalletRpc())

    assert result.summaries is not None
    assert result.summaries.transactions == 0


def failing_wallet() -> FakeWalletRpc:
    failing = wallet()
    failing.fail_on_call = 1
    failing.failure = WalletUnreachableError("connection refused")
    return failing


def invalid_import(tmp_path: Path) -> CliOptions:
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text("date_utc,usd_price\nnot-a-date,1\n")
    return CliOptions(db_path=str(tmp_path / "xmr.db"), import_prices=str(csv_path))


def reports_path_is_a_file(tmp_path: Path) -> CliOptions:
    not_a_directory = tmp_path / "reports"
    not_a_directory.write_text("a file")
    return CliOptions(db_path=str(tmp_path / "xmr.db"), reports_path=str(not_a_directory))


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(lambda tmp_path: (failing_wallet(), None), id="sync"),
        pytest.param(lambda tmp_path: (wallet(), invalid_import(tmp_path)), id="import file"),
        pytest.param(lambda tmp_path: (wallet(), reports_path_is_a_file(tmp_path)), id="export"),
    ],
)
def test_a_failure_before_the_export_builds_no_summaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: Callable[[Path], tuple[FakeWalletRpc, CliOptions | None]],
) -> None:
    built: list[object] = []

    def watched_build(*args: object) -> IncomeSummaries:
        built.append(args)
        raise AssertionError("build_summaries must not run")

    monkeypatch.setattr(run_module, "build_summaries", watched_build)
    failing, options = failure(tmp_path)

    with pytest.raises(RunError) as raised:
        summary_run(tmp_path / "xmr.db", failing, options)

    assert not isinstance(raised.value, SummaryError)
    assert built == []


def test_the_summary_step_changes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    changes: list[tuple[int, int]] = []
    written: list[bytes] = []
    real_write = run_module.write_export_file

    def watched_reader(conn: sqlite3.Connection) -> list[ExportRecord]:
        before = conn.total_changes
        found = export_records(conn)
        changes.append((before, conn.total_changes))
        return found

    def watched_write(directory: Path, rows: Sequence[object]) -> ExportSummary:
        summary: ExportSummary = real_write(directory, rows)
        written.append(summary.path.read_bytes())
        return summary

    monkeypatch.setattr(run_module, "write_export_file", watched_write)

    result = summary_run(tmp_path / "xmr.db", wallet(), summary_reader=watched_reader)

    ((before, after),) = changes
    assert before == after
    assert result.exported is not None
    assert result.exported.path.read_bytes() == written[0]
    assert result.summaries is not None
