"""The thin CLI: options in, one line out. run() is replaced; nothing real runs."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from monero_income import cli
from monero_income.orchestration import CliOptions, PricingSummary, Reporter, RunResult

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
