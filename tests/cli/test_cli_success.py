"""The thin CLI: options in, one line out. run() is replaced; nothing real runs."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from monero_income import cli
from monero_income.orchestration import (
    CliOptions,
    PricingSummary,
    Reporter,
    RunResult,
    StopReason,
)

runner = CliRunner()


class FakeRun:
    def __init__(self, recorded: int, pricing: PricingSummary | None = None) -> None:
        self.recorded = recorded
        self.pricing = pricing or PricingSummary()
        self.options: list[CliOptions] = []

    def __call__(self, options: CliOptions, reporter: Reporter) -> RunResult:
        self.options.append(options)
        return RunResult(recorded=self.recorded, pricing=self.pricing)


@pytest.mark.parametrize(
    ("recorded", "line"),
    [(1, "Recorded 1 new transaction.\n"), (3, "Recorded 3 new transactions.\n")],
)
def test_success_prints_one_line(monkeypatch: pytest.MonkeyPatch, recorded: int, line: str) -> None:
    monkeypatch.setattr(cli, "run", FakeRun(recorded))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert result.stdout == line


def test_options_map_onto_cli_options(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake = FakeRun(1)
    monkeypatch.setattr(cli, "run", fake)
    db_path = str(tmp_path / "x.db")

    result = runner.invoke(
        cli.app,
        [
            "--rpc-url",
            "http://127.0.0.1:18083/json_rpc",
            "--username",
            "monero",
            "--db-path",
            db_path,
        ],
    )

    assert result.exit_code == 0
    assert fake.options == [
        CliOptions(rpc_url="http://127.0.0.1:18083/json_rpc", username="monero", db_path=db_path)
    ]


def test_no_options_means_all_none(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun(1)
    monkeypatch.setattr(cli, "run", fake)

    runner.invoke(cli.app, [])

    assert fake.options == [CliOptions()]


def test_help_has_no_password_option_and_no_subcommands() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "--rpc-url" in result.stdout
    assert "--password" not in result.stdout
    assert "Commands" not in result.stdout


def test_nothing_new_prints_no_new_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "run", FakeRun(0))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert result.stdout == "No new transactions found.\n"


# --- feature 002: pricing lines ---------------------------------------------------------------

KEY = "CG-Zq9!distinctive-key"


@pytest.mark.parametrize(
    ("priced", "provisional", "line"),
    [
        (3, 1, "Priced 3 days (1 provisional).\n"),
        (2, 0, "Priced 2 days.\n"),
        (1, 0, "Priced 1 day.\n"),
        (1, 1, "Priced 1 day (1 provisional).\n"),
    ],
)
def test_priced_line_follows_the_sync_line(
    monkeypatch: pytest.MonkeyPatch, priced: int, provisional: int, line: str
) -> None:
    pricing = PricingSummary(priced=priced, provisional=provisional)
    monkeypatch.setattr(cli, "run", FakeRun(2, pricing))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert result.stdout == "Recorded 2 new transactions.\n" + line


def test_all_transactions_valued_line(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "run", FakeRun(0, PricingSummary(all_final=True)))

    result = runner.invoke(cli.app, [])

    assert result.stdout == "No new transactions found.\nAll transactions are valued.\n"


def test_empty_database_never_says_all_valued(monkeypatch: pytest.MonkeyPatch) -> None:
    # all_days_final is False when no transaction is recorded, so the line isn't printed.
    monkeypatch.setattr(cli, "run", FakeRun(0, PricingSummary(all_final=False)))

    result = runner.invoke(cli.app, [])

    assert result.stdout == "No new transactions found.\n"


def test_key_options_map_onto_cli_options(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeRun(1)
    monkeypatch.setattr(cli, "run", fake)

    result = runner.invoke(cli.app, ["--coingecko-api-key", KEY, "--coingecko-api-key-type", "pro"])

    assert result.exit_code == 0
    assert fake.options == [CliOptions(coingecko_api_key=KEY, coingecko_api_key_type="pro")]
    assert KEY not in result.output  # SC-008


@pytest.mark.parametrize(
    ("pricing", "lines"),
    [
        (PricingSummary(no_price=6), ["6 days still have no price; a later run will try again."]),
        (PricingSummary(no_price=1), ["1 day still has no price; a later run will try again."]),
        (
            PricingSummary(not_refreshed=2),
            ["2 provisional prices couldn't be refreshed; a later run will try again."],
        ),
        (
            PricingSummary(not_refreshed=1),
            ["1 provisional price couldn't be refreshed; a later run will try again."],
        ),
    ],
)
def test_lines_for_days_still_needing_a_price(
    monkeypatch: pytest.MonkeyPatch, pricing: PricingSummary, lines: list[str]
) -> None:
    monkeypatch.setattr(cli, "run", FakeRun(1, pricing))

    result = runner.invoke(cli.app, [])

    assert result.stdout.splitlines() == ["Recorded 1 new transaction.", *lines]


@pytest.mark.parametrize(
    ("stopped", "warning"),
    [
        (
            StopReason("rate_limited", "the price source is rate-limiting requests"),
            "Warning: price lookups stopped: the price source is rate-limiting requests",
        ),
        (
            StopReason("key_rejected", "the price source rejected the API key"),
            "Warning: price lookups stopped: the price source rejected the API key",
        ),
        (
            StopReason("unavailable", "cannot reach the price source: HTTP 503"),
            "Warning: price lookups stopped: cannot reach the price source: HTTP 503",
        ),
    ],
)
def test_stop_warning_goes_to_stderr_and_the_run_succeeds(
    monkeypatch: pytest.MonkeyPatch, stopped: StopReason, warning: str
) -> None:
    pricing = PricingSummary(priced=2, no_price=3, stopped=stopped)
    monkeypatch.setattr(cli, "run", FakeRun(1, pricing))

    result = runner.invoke(
        cli.app, ["--coingecko-api-key", KEY, "--coingecko-api-key-type", "demo"]
    )

    assert result.exit_code == 0
    assert result.stderr == warning + "\n"
    assert "Traceback" not in result.output
    assert KEY not in result.output


@pytest.mark.parametrize(
    ("too_old", "line"),
    [
        (
            2,
            "2 days are older than the price history and can't be looked up;"
            " use --import-prices to add them.",
        ),
        (
            1,
            "1 day is older than the price history and can't be looked up;"
            " use --import-prices to add it.",
        ),
    ],
)
def test_too_old_line(monkeypatch: pytest.MonkeyPatch, too_old: int, line: str) -> None:
    monkeypatch.setattr(cli, "run", FakeRun(1, PricingSummary(no_price=1, too_old=too_old)))

    result = runner.invoke(cli.app, [])

    assert result.stdout.splitlines() == [
        "Recorded 1 new transaction.",
        "1 day still has no price; a later run will try again.",
        line,
    ]
