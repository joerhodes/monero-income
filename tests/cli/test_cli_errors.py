"""The CLI turns every failure into one 'Error:' line and an exit code; never a traceback."""

import pytest
from typer.testing import CliRunner

from monero_income import cli
from monero_income.orchestration import CliOptions, Reporter, RunError, SyncResult

runner = CliRunner()


def raising(error: BaseException) -> object:
    def fake_run(options: CliOptions, reporter: Reporter) -> SyncResult:
        raise error

    return fake_run


@pytest.mark.parametrize(
    ("error", "line", "exit_code"),
    [
        (RunError("x"), "Error: x\n", 1),
        (KeyboardInterrupt(), "Error: interrupted; anything already recorded was kept\n", 130),
        (ValueError("boom"), "Error: unexpected ValueError: boom\n", 1),
    ],
)
def test_failures_are_one_line_with_exit_code(
    monkeypatch: pytest.MonkeyPatch, error: BaseException, line: str, exit_code: int
) -> None:
    monkeypatch.setattr(cli, "run", raising(error))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == exit_code
    assert result.stderr == line
    assert result.stdout == ""
    assert "Traceback" not in result.output


def test_unknown_option_is_a_usage_error() -> None:
    result = runner.invoke(cli.app, ["--password", "x"])

    assert result.exit_code == 2
    assert "Traceback" not in result.output


def test_warning_is_printed_and_the_run_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(options: CliOptions, reporter: Reporter) -> SyncResult:
        reporter.warning("config file is readable by other users")
        return SyncResult(recorded=2)

    monkeypatch.setattr(cli, "run", fake_run)

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert result.stderr == "Warning: config file is readable by other users\n"
    assert result.stdout == "Recorded 2 new transactions.\n"
    assert "Traceback" not in result.output
