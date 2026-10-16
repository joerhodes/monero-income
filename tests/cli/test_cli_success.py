"""The thin CLI: options in, one line out. run() is replaced; nothing real runs."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from monero_income import cli
from monero_income.orchestration import CliOptions, Reporter, SyncResult

runner = CliRunner()


class FakeRun:
    def __init__(self, recorded: int) -> None:
        self.recorded = recorded
        self.options: list[CliOptions] = []

    def __call__(self, options: CliOptions, reporter: Reporter) -> SyncResult:
        self.options.append(options)
        return SyncResult(recorded=self.recorded)


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
